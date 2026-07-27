"""Tests for fix_parsers day-title derivation.

Run:
    cd Portfolio_Site/reports && python3 -m unittest test_fix_parsers -v
"""
from __future__ import annotations

import unittest

from fix_parsers import day_title, day_title_from_h1


class DayTitleFromH1Test(unittest.TestCase):
    def test_a_comma_less_heading_normalizes(self):
        # Units 13-15 write "Unit 13 Day 1 Lesson Plan" with no comma, which is
        # what the original parser missed, leaving nine day titles empty.
        self.assertEqual(
            day_title_from_h1(13, 1, "Unit 13 Day 1 Lesson Plan"), "Unit 13, Day 1"
        )

    def test_a_comma_heading_normalizes_the_same_way(self):
        self.assertEqual(
            day_title_from_h1(12, 1, "Unit 12, Day 1 Lesson Plan"), "Unit 12, Day 1"
        )

    def test_a_descriptive_heading_keeps_its_subtitle(self):
        self.assertEqual(
            day_title_from_h1(1, 1, "Unit 1, Day 1: Welcome to Advanced Computer Science"),
            "Unit 1, Day 1: Welcome to Advanced Computer Science",
        )

    def test_an_unrecognized_heading_falls_back_to_the_canonical_form(self):
        self.assertEqual(day_title_from_h1(9, 4, "Something else entirely"), "Unit 9, Day 4")

    def test_an_empty_heading_falls_back(self):
        self.assertEqual(day_title_from_h1(9, 4, ""), "Unit 9, Day 4")

    def test_a_trailing_separator_is_trimmed(self):
        self.assertEqual(day_title_from_h1(5, 2, "Unit 5 Day 2 Lesson Plan —"), "Unit 5, Day 2")


class DayTitleTest(unittest.TestCase):
    """Against the real lesson plans, since that is the source of truth."""

    def test_reads_a_real_comma_less_unit(self):
        self.assertEqual(day_title(13, 1), "Unit 13, Day 1")

    def test_reads_a_real_descriptive_unit(self):
        self.assertEqual(day_title(1, 1), "Unit 1, Day 1: Welcome to Advanced Computer Science")

    def test_returns_none_when_there_is_no_lesson_plan(self):
        # None means "keep whatever is already there", matching day_standards.
        self.assertIsNone(day_title(99, 1))

    def test_every_previously_empty_day_now_resolves(self):
        for unit, days in ((13, (1, 2)), (14, (1, 2, 3, 4, 5)), (15, (1, 2))):
            for day in days:
                with self.subTest(unit=unit, day=day):
                    self.assertEqual(day_title(unit, day), f"Unit {unit}, Day {day}")


if __name__ == "__main__":
    unittest.main()
