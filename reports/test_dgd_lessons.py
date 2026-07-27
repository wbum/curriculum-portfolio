"""Tests for DGD I lesson-file parsing.

Run:
    cd Portfolio_Site/reports && python3 -m unittest test_dgd_lessons -v
"""
from __future__ import annotations

import unittest
from pathlib import Path

from dgd_lessons import LESSONS_DIR, parse_meetings, parse_unit_title, unit_lesson_files

UNIT_1 = """# Unit 1: The Industry & You — Lesson Plans

## WEEK 1 · SESSION 1 (MON, 40 min) — Course Overview & What You'll Build
**Standards:** DGD.1.1.1, DGD.1.5.1

### Learning Objectives
- Something

## WEEK 1 · SESSION 2 (TUE, 40 min) — CTE Pathway, CTSOs & Credentials
**Standards:** DGD.1.1.2

## WEEK 1 · FRIDAY 1 (FRI, 50 min) — Non-Digital Game Reflection
**Standards:** DGD.2.1.2

## WEEK 2 · SESSION 3 (MON, 40 min) — Video Game Evolution
No standards line here.
"""


class ParseUnitTitleTest(unittest.TestCase):
    def test_strips_the_unit_prefix_and_lesson_plans_suffix(self):
        self.assertEqual(parse_unit_title(UNIT_1), "The Industry & You")

    def test_falls_back_to_empty_when_there_is_no_h1(self):
        self.assertEqual(parse_unit_title("no heading here"), "")


class ParseMeetingsTest(unittest.TestCase):
    def test_finds_every_class_meeting(self):
        self.assertEqual(len(parse_meetings(UNIT_1)), 4)

    def test_numbers_meetings_chronologically_not_by_session_number(self):
        # A Friday sits between SESSION 2 and SESSION 3, so day numbers must follow
        # document order or they collide -- SESSION 1 and FRIDAY 1 are both "1".
        self.assertEqual([m["day"] for m in parse_meetings(UNIT_1)], [1, 2, 3, 4])

    def test_title_is_the_topic_after_the_dash(self):
        self.assertEqual(
            parse_meetings(UNIT_1)[0]["title"], "Course Overview & What You'll Build"
        )

    def test_a_friday_is_a_meeting_like_any_other(self):
        friday = parse_meetings(UNIT_1)[2]
        self.assertEqual(friday["title"], "Non-Digital Game Reflection")
        self.assertEqual(friday["day"], 3)

    def test_reads_the_standards_line(self):
        self.assertEqual(parse_meetings(UNIT_1)[0]["standards"], ["1.1.1", "1.5.1"])

    def test_strips_the_dgd_prefix_from_codes(self):
        self.assertNotIn("DGD", "".join(parse_meetings(UNIT_1)[0]["standards"]))

    def test_a_meeting_with_no_standards_line_gets_an_empty_list(self):
        self.assertEqual(parse_meetings(UNIT_1)[3]["standards"], [])

    def test_does_not_pull_standards_from_the_next_meeting(self):
        self.assertEqual(parse_meetings(UNIT_1)[1]["standards"], ["1.1.2"])

    def test_deduplicates_repeated_codes(self):
        text = "## WEEK 1 · SESSION 1 (MON, 40 min) — T\n**Standards:** DGD.1.1.1, DGD.1.1.1\n"
        self.assertEqual(parse_meetings(text)[0]["standards"], ["1.1.1"])

    def test_ignores_a_heading_that_is_not_a_meeting(self):
        text = UNIT_1 + "\n## Unit Assessment\n**Standards:** DGD.9.9.9\n"
        self.assertEqual(len(parse_meetings(text)), 4)

    def test_returns_nothing_for_a_file_with_no_meetings(self):
        self.assertEqual(parse_meetings("# Unit 9: Something\n\n## Overview\ntext\n"), [])

    def test_tolerates_a_missing_time_parenthetical(self):
        text = "## WEEK 1 · SESSION 1 — Just A Title\n"
        self.assertEqual(parse_meetings(text)[0]["title"], "Just A Title")


class RealFilesTest(unittest.TestCase):
    """Against the actual DGD I lesson files, which are the source of truth."""

    def test_finds_all_eight_units(self):
        self.assertEqual([n for n, _ in unit_lesson_files()], [1, 2, 3, 4, 5, 6, 7, 8])

    def test_every_unit_yields_meetings(self):
        # The whole point: the old parser matched zero and would have published
        # eight empty units.
        for num, path in unit_lesson_files():
            with self.subTest(unit=num):
                self.assertGreater(len(parse_meetings(path.read_text())), 0)

    def test_meeting_counts_match_the_heading_counts(self):
        for num, path in unit_lesson_files():
            text = path.read_text()
            expected = sum(
                1 for line in text.splitlines()
                if line.startswith("## WEEK ") and ("SESSION" in line or "FRIDAY" in line)
            )
            with self.subTest(unit=num):
                self.assertEqual(len(parse_meetings(text)), expected)

    def test_day_numbers_are_unique_within_every_unit(self):
        for num, path in unit_lesson_files():
            days = [m["day"] for m in parse_meetings(path.read_text())]
            with self.subTest(unit=num):
                self.assertEqual(len(days), len(set(days)))

    def test_every_unit_has_a_title(self):
        for num, path in unit_lesson_files():
            with self.subTest(unit=num):
                self.assertTrue(parse_unit_title(path.read_text()).strip())

    def test_the_lesson_directory_exists(self):
        self.assertTrue(Path(LESSONS_DIR).is_dir())


if __name__ == "__main__":
    unittest.main()
