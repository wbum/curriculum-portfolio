#!/usr/bin/env python3
"""Validate the crosswalk datasets before they get published.

The site reads two kinds of JSON per course:

  catalog     <course>_cs_standards_grounded.json
              {strand: {title, performance_standards: {code: {title, indicators:
              {code: {description, level}}}}}}

  course map  <course>_course_map_grounded.json
              {units: [{number, title, days: [{day, title, standards: [code]}],
              standards: [code]}], standards: {code: description}}

Nothing enforced either shape, which matters because `indexData()` in
crosswalk.js drops a day tag that is not in the catalog *silently*:

    if (stdToLessons[normCode]) { ...push... }

A typo in a lesson plan's standards section therefore vanishes from coverage
instead of raising anything, and the site publishes a lower percentage with no
indication that it is wrong. That class of failure is already on record in
99_System/AUTOMATION.md section 5.

Errors vs warnings: an error is something that breaks or silently distorts the
published site, and it blocks the write. A warning is bad data the site does not
read -- currently the course map's top-level `standards` description map, which
holds parser wreckage in the ACS file but is never rendered.

Usage:
    python3 validate_data.py            # check every committed file, exit 1 on error
    python3 validate_data.py --quiet    # only print problems
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPORTS = Path(__file__).parent

# course -> (catalog file, course map file). Mirrors loadData() in crosswalk.js.
COURSE_FILES = {
    "acs_i": ("nv_cs_standards_grounded.json", "acs1_course_map_grounded.json"),
    "wdd_i": ("wdd_cs_standards_grounded.json", "wdd_course_map_grounded.json"),
    "dgd_i": ("dgd_cs_standards_grounded.json", "dgd_course_map_grounded.json"),
    "dgd_ii": ("dgd_cs_standards_grounded.json", "dgd2_course_map_grounded.json"),
    "cet": ("cet_cs_standards_grounded.json", "cet_course_map_grounded.json"),
}

# Prefixes normalizeCode() in crosswalk.js strips. Kept in the same order so the
# validator and the site always agree about which codes resolve.
CODE_PREFIXES = ("ADVCS.", "WDD ", "WEB ", "DGD.", "DGD ", "9-12.")

# A description that is really the tail of a split code list: leading punctuation,
# or nothing but codes and separators.
CODE_FRAGMENT_RE = re.compile(r"^[\s,;.]|^[\d.]+(\s*,\s*[\d.]+)*\)?$")


class ValidationError(Exception):
    """Raised instead of writing data that would break the published site."""


@dataclass(frozen=True)
class Issue:
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.where}: {self.message}"


@dataclass(frozen=True)
class Report:
    errors: tuple[Issue, ...] = ()
    warnings: tuple[Issue, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors

    def __add__(self, other: "Report") -> "Report":
        return Report(self.errors + other.errors, self.warnings + other.warnings)


def normalize_code(code: str) -> str:
    """Mirror normalizeCode() in crosswalk.js."""
    for prefix in CODE_PREFIXES:
        code = code.replace(prefix, "")
    return code.strip()


def catalog_indicators(catalog: dict) -> dict[str, dict]:
    """Flatten a catalog to indicator code -> indicator.

    Works for both key styles: numeric strands ("1.0") and CET's frameworks
    ("CS"/"IT"). Only the nesting matters, not what the strands are called.
    """
    out: dict[str, dict] = {}
    for strand in catalog.values():
        if not isinstance(strand, dict):
            continue
        for perf in (strand.get("performance_standards") or {}).values():
            if not isinstance(perf, dict):
                continue
            for code, indicator in (perf.get("indicators") or {}).items():
                out[code] = indicator
    return out


def _nonempty_str(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_catalog(catalog, name: str) -> Report:
    errors: list[Issue] = []

    if not isinstance(catalog, dict):
        return Report((Issue(name, f"expected an object, got {type(catalog).__name__}"),))
    if not catalog:
        return Report((Issue(name, "catalog is empty"),))

    for strand_code, strand in catalog.items():
        at = f"{name} → {strand_code}"
        if not isinstance(strand, dict):
            errors.append(Issue(at, "strand is not an object"))
            continue
        if not _nonempty_str(strand.get("title")):
            errors.append(Issue(at, "missing a title"))

        perfs = strand.get("performance_standards")
        if not isinstance(perfs, dict) or not perfs:
            errors.append(Issue(at, "missing or empty performance_standards"))
            continue

        for perf_code, perf in perfs.items():
            at_perf = f"{at}/{perf_code}"
            if not isinstance(perf, dict):
                errors.append(Issue(at_perf, "performance standard is not an object"))
                continue
            if not _nonempty_str(perf.get("title")):
                errors.append(Issue(at_perf, "missing a title"))

            indicators = perf.get("indicators")
            if not isinstance(indicators, dict) or not indicators:
                errors.append(Issue(at_perf, "missing or empty indicators"))
                continue

            for ind_code, indicator in indicators.items():
                at_ind = f"{at_perf}/{ind_code}"
                if not isinstance(indicator, dict):
                    errors.append(Issue(at_ind, "indicator is not an object"))
                    continue
                if not _nonempty_str(indicator.get("description")):
                    errors.append(Issue(at_ind, "missing a description"))
                # crosswalk.js falls back to 'L1' for a missing level, which moves
                # the indicator in scope and changes the published percentage.
                if not _nonempty_str(indicator.get("level")):
                    errors.append(Issue(at_ind, "missing a level (site would assume L1)"))

    return Report(tuple(errors))


def validate_course_map(course_map, name: str) -> Report:
    errors: list[Issue] = []
    warnings: list[Issue] = []

    if not isinstance(course_map, dict):
        return Report((Issue(name, f"expected an object, got {type(course_map).__name__}"),))

    units = course_map.get("units")
    if not isinstance(units, list) or not units:
        errors.append(Issue(name, "missing or empty units"))
        units = []

    seen_units: set = set()
    for index, unit in enumerate(units):
        at = f"{name} → unit[{index}]"
        if not isinstance(unit, dict):
            errors.append(Issue(at, "unit is not an object"))
            continue

        number = unit.get("number")
        if not isinstance(number, int) or isinstance(number, bool):
            errors.append(Issue(at, f"unit number must be an integer, got {number!r}"))
        elif number in seen_units:
            errors.append(Issue(at, f"duplicate unit number {number}"))
        else:
            seen_units.add(number)
            at = f"{name} → Unit {number}"

        if not _nonempty_str(unit.get("title")):
            errors.append(Issue(at, "missing a title"))

        days = unit.get("days")
        if not isinstance(days, list) or not days:
            errors.append(Issue(at, "missing or empty days"))
            continue

        seen_days: set = set()
        for day in days:
            if not isinstance(day, dict):
                errors.append(Issue(at, "day is not an object"))
                continue
            day_num = day.get("day")
            at_day = f"{at}, Day {day_num}"
            if not isinstance(day_num, int) or isinstance(day_num, bool):
                errors.append(Issue(at_day, f"day number must be an integer, got {day_num!r}"))
            elif day_num in seen_days:
                errors.append(Issue(at_day, f"duplicate day number {day_num}"))
            else:
                seen_days.add(day_num)

            if not _nonempty_str(day.get("title")):
                errors.append(Issue(at_day, "missing a title"))

            codes = day.get("standards")
            if codes is None:
                codes = []
            if not isinstance(codes, list):
                errors.append(Issue(at_day, "standards must be a list"))
                continue
            for code in codes:
                if not _nonempty_str(code):
                    errors.append(Issue(at_day, f"standard code must be a string, got {code!r}"))

    # The top-level description map. crosswalk.js never reads it -- descriptions
    # come from the catalog -- so wreckage here is a warning, not a failure.
    descriptions = course_map.get("standards")
    if descriptions is None:
        warnings.append(Issue(name, "no top-level standards map"))
    elif not isinstance(descriptions, dict):
        errors.append(Issue(name, "top-level standards must be an object"))
    else:
        for code, description in descriptions.items():
            if not _nonempty_str(description):
                warnings.append(Issue(f"{name} → {code}", "description is empty"))
            elif CODE_FRAGMENT_RE.match(description.strip()):
                warnings.append(
                    Issue(
                        f"{name} → {code}",
                        f"description looks like a split code list: {description.strip()!r}",
                    )
                )

    return Report(tuple(errors), tuple(warnings))


def validate_pair(catalog, course_map, course: str) -> Report:
    """Every day tag must resolve to a catalog indicator.

    This is the check the site cannot make for itself: crosswalk.js drops an
    unresolvable tag without comment, so the coverage percentage silently drops
    instead of the build failing.
    """
    indicators = catalog_indicators(catalog)
    if not indicators:
        return Report((Issue(course, "catalog has no indicators to resolve against"),))

    errors: list[Issue] = []
    for unit in course_map.get("units") or []:
        if not isinstance(unit, dict):
            continue
        for day in unit.get("days") or []:
            if not isinstance(day, dict):
                continue
            for code in day.get("standards") or []:
                if not _nonempty_str(code):
                    continue
                if normalize_code(code) not in indicators:
                    errors.append(
                        Issue(
                            f"{course} → Unit {unit.get('number')}, Day {day.get('day')}",
                            f"standard {code!r} is not in the catalog — "
                            "the site will drop it and under-report coverage",
                        )
                    )
    return Report(tuple(errors))


def validate_all(reports_dir: Path | None = None) -> Report:
    """Validate every committed dataset, including each course's cross-check."""
    reports_dir = reports_dir or REPORTS
    report = Report()
    catalogs: dict[str, dict] = {}

    for course, (catalog_name, map_name) in COURSE_FILES.items():
        catalog_path = reports_dir / catalog_name
        map_path = reports_dir / map_name

        for path in (catalog_path, map_path):
            if not path.is_file():
                report += Report((Issue(course, f"missing data file {path.name}"),))

        if not catalog_path.is_file() or not map_path.is_file():
            continue

        # Catalogs are shared between courses (dgd_i and dgd_ii), so validate
        # each one once and reuse it for the cross-check.
        if catalog_name not in catalogs:
            catalogs[catalog_name] = json.loads(catalog_path.read_text(encoding="utf-8"))
            report += validate_catalog(catalogs[catalog_name], catalog_name)
        catalog = catalogs[catalog_name]

        course_map = json.loads(map_path.read_text(encoding="utf-8"))
        report += validate_course_map(course_map, map_name)
        report += validate_pair(catalog, course_map, course)

    return report


def write_json_validated(path, data, kind: str, indent: int = 2) -> None:
    """Validate, then write. Raises ValidationError instead of publishing junk.

    On failure the existing file is left exactly as it was, so a bad generator
    run cannot replace good data with broken data.
    """
    validators = {"course_map": validate_course_map, "catalog": validate_catalog}
    if kind not in validators:
        raise ValueError(f"unknown kind {kind!r}; expected one of {sorted(validators)}")

    path = Path(path)
    report = validators[kind](data, path.name)
    for warning in report.warnings:
        print(f"  warning: {warning}", file=sys.stderr)
    if not report.ok:
        detail = "\n".join(f"  {issue}" for issue in report.errors)
        raise ValidationError(f"refusing to write {path.name}:\n{detail}")

    path.write_text(json.dumps(data, indent=indent), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quiet", action="store_true", help="only print problems")
    args = ap.parse_args()

    report = validate_all()

    for warning in report.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    for error in report.errors:
        print(f"ERROR:   {error}", file=sys.stderr)

    if report.errors:
        print(
            f"\n{len(report.errors)} error(s), {len(report.warnings)} warning(s). "
            "Data would publish a broken crosswalk.",
            file=sys.stderr,
        )
        return 1
    if not args.quiet:
        print(
            f"All {len(COURSE_FILES)} courses validate "
            f"({len(report.warnings)} warning(s), none site-affecting)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
