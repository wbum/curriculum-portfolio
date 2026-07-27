"""Tests for crosswalk data validation.

Run:
    cd Portfolio_Site/reports && python3 -m unittest test_validate_data -v
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from validate_data import (
    ValidationError,
    catalog_indicators,
    normalize_code,
    validate_catalog,
    validate_course_map,
    validate_pair,
    write_json_validated,
)


def catalog(indicators=("1.1.1",)):
    return {
        "1.0": {
            "title": "CONTENT STANDARD ONE",
            "performance_standards": {
                "1.1": {
                    "title": "Performance one",
                    "indicators": {
                        code: {"description": f"Do the thing {code}", "level": "L1"}
                        for code in indicators
                    },
                }
            },
        }
    }


def course_map(day_standards=("1.1.1",), units=None):
    return {
        "units": units
        or [
            {
                "number": 1,
                "title": "Unit One",
                "days": [
                    {"day": 1, "title": "Unit 1, Day 1", "standards": list(day_standards)}
                ],
                "standards": list(day_standards),
            }
        ],
        "standards": {code: f"Do the thing {code}" for code in day_standards},
    }


class NormalizeCodeTest(unittest.TestCase):
    """Must match normalizeCode() in crosswalk.js or the site and the validator
    will disagree about which codes resolve."""

    def test_strips_the_advcs_prefix(self):
        self.assertEqual(normalize_code("ADVCS.2.1.2"), "2.1.2")

    def test_strips_course_prefixes(self):
        self.assertEqual(normalize_code("WDD 1.1.1"), "1.1.1")
        self.assertEqual(normalize_code("WEB 1.1.1"), "1.1.1")
        self.assertEqual(normalize_code("DGD.1.1.1"), "1.1.1")
        self.assertEqual(normalize_code("DGD 1.1.1"), "1.1.1")

    def test_strips_the_grade_band(self):
        self.assertEqual(normalize_code("9-12.AP.A.1"), "AP.A.1")

    def test_trims_whitespace(self):
        self.assertEqual(normalize_code("  1.1.1  "), "1.1.1")

    def test_leaves_a_bare_code_alone(self):
        self.assertEqual(normalize_code("1.1.1"), "1.1.1")


class CatalogIndicatorsTest(unittest.TestCase):
    def test_flattens_to_indicator_codes(self):
        self.assertEqual(set(catalog_indicators(catalog(("1.1.1", "1.1.2")))), {"1.1.1", "1.1.2"})

    def test_handles_the_cet_two_framework_shape(self):
        # CET keys its strands "CS"/"IT" rather than "1.0"/"2.0".
        cat = {"CS": catalog(("AP.A.1",))["1.0"], "IT": catalog(("NI.C.1",))["1.0"]}
        self.assertEqual(set(catalog_indicators(cat)), {"AP.A.1", "NI.C.1"})

    def test_an_empty_catalog_flattens_to_nothing(self):
        self.assertEqual(catalog_indicators({}), {})


class ValidateCatalogTest(unittest.TestCase):
    def test_a_good_catalog_passes(self):
        self.assertTrue(validate_catalog(catalog(), "cat.json").ok)

    def test_an_empty_catalog_fails(self):
        self.assertFalse(validate_catalog({}, "cat.json").ok)

    def test_a_non_dict_fails(self):
        self.assertFalse(validate_catalog([], "cat.json").ok)

    def test_a_strand_without_performance_standards_fails(self):
        self.assertFalse(validate_catalog({"1.0": {"title": "x"}}, "cat.json").ok)

    def test_a_performance_standard_without_indicators_fails(self):
        cat = catalog()
        cat["1.0"]["performance_standards"]["1.1"]["indicators"] = {}
        self.assertFalse(validate_catalog(cat, "cat.json").ok)

    def test_an_indicator_without_a_description_fails(self):
        cat = catalog()
        cat["1.0"]["performance_standards"]["1.1"]["indicators"]["1.1.1"]["description"] = ""
        self.assertFalse(validate_catalog(cat, "cat.json").ok)

    def test_an_indicator_without_a_level_fails(self):
        # crosswalk.js defaults a missing level to L1, which silently moves an
        # indicator in scope and changes the published coverage percentage.
        cat = catalog()
        del cat["1.0"]["performance_standards"]["1.1"]["indicators"]["1.1.1"]["level"]
        report = validate_catalog(cat, "cat.json")

        self.assertFalse(report.ok)
        self.assertTrue(any("level" in i.message for i in report.errors))

    def test_the_error_names_the_indicator(self):
        cat = catalog()
        cat["1.0"]["performance_standards"]["1.1"]["indicators"]["1.1.1"]["description"] = ""
        self.assertTrue(any("1.1.1" in i.where for i in validate_catalog(cat, "cat.json").errors))


class ValidateCourseMapTest(unittest.TestCase):
    def test_a_good_course_map_passes(self):
        self.assertTrue(validate_course_map(course_map(), "cm.json").ok)

    def test_missing_units_fails(self):
        self.assertFalse(validate_course_map({"standards": {}}, "cm.json").ok)

    def test_empty_units_fails(self):
        self.assertFalse(validate_course_map({"units": [], "standards": {}}, "cm.json").ok)

    def test_a_duplicate_unit_number_fails(self):
        cm = course_map()
        cm["units"].append(dict(cm["units"][0]))
        report = validate_course_map(cm, "cm.json")

        self.assertFalse(report.ok)
        self.assertTrue(any("duplicate" in i.message.lower() for i in report.errors))

    def test_a_duplicate_day_number_within_a_unit_fails(self):
        cm = course_map()
        cm["units"][0]["days"].append(dict(cm["units"][0]["days"][0]))
        self.assertFalse(validate_course_map(cm, "cm.json").ok)

    def test_the_same_day_number_in_different_units_is_fine(self):
        cm = course_map()
        second = json.loads(json.dumps(cm["units"][0]))
        second["number"] = 2
        cm["units"].append(second)
        self.assertTrue(validate_course_map(cm, "cm.json").ok)

    def test_a_unit_without_a_title_fails(self):
        cm = course_map()
        cm["units"][0]["title"] = ""
        self.assertFalse(validate_course_map(cm, "cm.json").ok)

    def test_a_non_integer_unit_number_fails(self):
        cm = course_map()
        cm["units"][0]["number"] = "1"
        self.assertFalse(validate_course_map(cm, "cm.json").ok)

    def test_a_unit_with_no_days_fails(self):
        cm = course_map()
        cm["units"][0]["days"] = []
        self.assertFalse(validate_course_map(cm, "cm.json").ok)

    def test_a_day_with_no_standards_is_allowed(self):
        # A day can legitimately teach nothing standards-tagged.
        cm = course_map()
        cm["units"][0]["days"][0]["standards"] = []
        self.assertTrue(validate_course_map(cm, "cm.json").ok)

    def test_a_non_string_standard_code_fails(self):
        cm = course_map()
        cm["units"][0]["days"][0]["standards"] = [111]
        self.assertFalse(validate_course_map(cm, "cm.json").ok)

    def test_a_code_list_fragment_as_a_description_warns(self):
        # Real corruption in acs1_course_map_grounded.json: a parser split a
        # comma-separated code list and kept the tail as the description. The
        # site does not read this map, so it warns rather than fails.
        cm = course_map()
        cm["standards"]["1.1.1"] = ", 2.1.4, 2.5.1"
        report = validate_course_map(cm, "cm.json")

        self.assertTrue(report.ok)
        self.assertTrue(any("1.1.1" in i.where for i in report.warnings))

    def test_an_empty_description_warns(self):
        cm = course_map()
        cm["standards"]["1.1.1"] = ""
        self.assertTrue(validate_course_map(cm, "cm.json").warnings)

    def test_real_prose_does_not_warn(self):
        self.assertEqual(validate_course_map(course_map(), "cm.json").warnings, ())


class ValidatePairTest(unittest.TestCase):
    """The check that matters: crosswalk.js drops a day tag that is not in the
    catalog, with no warning, so coverage silently under-reports."""

    def test_matching_data_passes(self):
        self.assertTrue(validate_pair(catalog(), course_map(), "acs_i").ok)

    def test_a_day_tag_missing_from_the_catalog_fails(self):
        report = validate_pair(catalog(("1.1.1",)), course_map(("9.9.9",)), "acs_i")

        self.assertFalse(report.ok)
        self.assertTrue(any("9.9.9" in i.message for i in report.errors))

    def test_the_error_says_where_the_tag_came_from(self):
        report = validate_pair(catalog(("1.1.1",)), course_map(("9.9.9",)), "acs_i")
        self.assertTrue(any("Unit 1" in i.where and "Day 1" in i.where for i in report.errors))

    def test_a_prefixed_tag_resolves_after_normalizing(self):
        self.assertTrue(validate_pair(catalog(("2.1.2",)), course_map(("ADVCS.2.1.2",)), "acs_i").ok)

    def test_an_uncovered_indicator_is_fine(self):
        # A gap is the crosswalk's whole subject, not an error.
        self.assertTrue(validate_pair(catalog(("1.1.1", "1.1.2")), course_map(("1.1.1",)), "acs_i").ok)


class WriteJsonValidatedTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "out.json"

    def test_writes_valid_data(self):
        write_json_validated(self.path, course_map(), "course_map")
        self.assertEqual(json.loads(self.path.read_text())["units"][0]["number"], 1)

    def test_refuses_to_write_invalid_data(self):
        with self.assertRaises(ValidationError):
            write_json_validated(self.path, {"units": []}, "course_map")

    def test_leaves_the_previous_file_intact_on_failure(self):
        write_json_validated(self.path, course_map(), "course_map")
        before = self.path.read_text()

        with self.assertRaises(ValidationError):
            write_json_validated(self.path, {"units": []}, "course_map")

        self.assertEqual(self.path.read_text(), before)

    def test_honours_the_indent_so_diffs_stay_small(self):
        write_json_validated(self.path, course_map(), "course_map", indent=1)
        self.assertIn('\n "units"', self.path.read_text())

    def test_validates_a_catalog_too(self):
        with self.assertRaises(ValidationError):
            write_json_validated(self.path, {}, "catalog")

    def test_rejects_an_unknown_kind(self):
        with self.assertRaises(ValueError):
            write_json_validated(self.path, course_map(), "nonsense")


class RealDataTest(unittest.TestCase):
    """The committed data must pass, or the gate is useless as a guard."""

    def setUp(self):
        self.reports = Path(__file__).parent

    def test_every_committed_file_validates(self):
        from validate_data import validate_all

        report = validate_all(self.reports)
        self.assertTrue(
            report.ok,
            "committed data has errors:\n"
            + "\n".join(f"  {i.where}: {i.message}" for i in report.errors),
        )


if __name__ == "__main__":
    unittest.main()
