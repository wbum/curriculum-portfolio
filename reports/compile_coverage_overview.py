#!/usr/bin/env python3
"""Cross-course standards coverage overview.

The per-course crosswalk JSON already maps each unit to the standards it teaches.
This rolls that up across ALL five courses into one report: for each course it
computes covered vs total indicators, the coverage %, and the exact uncovered
(gap) indicator codes with descriptions.

This is the mechanical, data-grounded complement to the hand-curated
*_standards_gap_status.md analyses (which add L1/L2 scope judgment for ACS and
WDD). It fills DGD I, DGD II, and CET — which had grounded data but no gap
summary — with at least a precise uncovered-indicator list.

Source of truth is the grounded JSON, which is regenerated from the lesson
markdown by the per-course compile scripts. Re-run this after those.

Output: reports/standards-coverage-overview.md
"""
from __future__ import annotations

import json
from pathlib import Path

REPORTS = Path(__file__).parent
OUT = REPORTS / "standards-coverage-overview.md"

# course key -> (display, course_map, standards_file, ctso_area, level)
# ctso_area: the CTSO/FBLA content area to report separately (excluded from
# "true" gaps per the WDD rule and ACS co-curricular treatment). None for CET.
# level: the course's CTE level; coverage is scored only against indicators whose
# level tag includes it, so an L1 course is not penalized for L2/Complementary
# indicators it isn't meant to teach. None = single-level course (no filtering).
COURSES = {
    "acs_i": ("ACS I", "acs1_course_map_grounded.json", "nv_cs_standards_grounded.json", "1.0", "L1"),
    "wdd_i": ("WDD I", "wdd_course_map_grounded.json", "wdd_cs_standards_grounded.json", "1.0", "L1"),
    "dgd_i": ("DGD I", "dgd_course_map_grounded.json", "dgd_cs_standards_grounded.json", "1.0", "L1"),
    "dgd_ii": ("DGD II", "dgd2_course_map_grounded.json", "dgd_cs_standards_grounded.json", "1.0", "L2"),
    "cet": ("CET", "cet_course_map_grounded.json", "cet_cs_standards_grounded.json", None, None),
}

# Courses that were built but never taught. Excluded from the summary table and the
# gap detail so no coverage claim on the site rests on a course students never took.
# The COURSES entry and the crosswalk JSON stay — they are the record of the build.
#
# dgd_ii: the one-year L2 bridge had no period on the 2026-27 master schedule and was
# superseded before it ran. The real DGD II is built fresh for 2027-28. Remove from
# this set only when a DGD II is actually scheduled and taught.
VOID_COURSES = {"dgd_ii"}


def normalize(code: str) -> str:
    """Unit standards use 'ADVCS.2.3.5'; standards files use bare '2.3.5'."""
    return code.replace("ADVCS.", "").strip()


def enumerate_indicators(standards_file: str) -> dict[str, dict]:
    """Return {indicator_code: {area, description, level}} for the whole doc."""
    data = json.load(open(REPORTS / standards_file))
    out: dict[str, dict] = {}
    for area_key, area in data.items():
        for ps in area.get("performance_standards", {}).values():
            for code, ind in ps.get("indicators", {}).items():
                out[code] = {
                    "area": area_key,
                    "description": (ind.get("description") or "").strip(),
                    "level": (ind.get("level") or "").strip(),
                }
    return out


def covered_codes(course_map: str) -> set[str]:
    """Union of day-level and unit-level standards tags.

    Day-level tags are the authoritative, richer source (the public crosswalk
    reads these); some maps also carry a unit-level summary. Union both so this
    report and the crosswalk agree.
    """
    data = json.load(open(REPORTS / course_map))
    covered: set[str] = set()
    for unit in data.get("units", []):
        for c in unit.get("standards", []):
            covered.add(normalize(c))
        for day in unit.get("days", []):
            for c in day.get("standards", []):
                covered.add(normalize(c))
    return covered


def pct(n: int, d: int) -> str:
    return f"{round(100 * n / d)}%" if d else "—"


def main() -> None:
    rows = []
    sections = []

    for key, (display, cmap, sfile, ctso, level) in COURSES.items():
        if key in VOID_COURSES:
            continue
        indicators = enumerate_indicators(sfile)
        covered = covered_codes(cmap)

        all_codes = set(indicators)
        # Split CTSO area out of "core" expectations.
        is_ctso = lambda c: ctso is not None and c.startswith(ctso.split(".")[0] + ".")
        core_codes = {c for c in all_codes if not is_ctso(c)}
        ctso_codes = all_codes - core_codes

        # An indicator is in-scope when its level tag includes the course's level
        # (or the indicator has no level data, or the course is single-level).
        def in_scope(c: str) -> bool:
            if level is None:
                return True
            lv = indicators[c]["level"]
            return (not lv) or (level in lv)

        scope_codes = {c for c in core_codes if in_scope(c)}
        out_of_level = core_codes - scope_codes

        core_covered = covered & scope_codes
        core_gaps = sorted(scope_codes - covered)
        ctso_covered = covered & ctso_codes

        rows.append(
            f"| {display} | {len(core_covered)}/{len(scope_codes)} | "
            f"{pct(len(core_covered), len(scope_codes))} | "
            f"{len(core_gaps)} | "
            f"{len(out_of_level)} | "
            f"{(str(len(ctso_covered)) + '/' + str(len(ctso_codes))) if ctso_codes else '—'} |"
        )

        # Per-course gap detail.
        lines = [f"### {display} — {len(core_gaps)} uncovered in-scope indicator(s)", ""]
        if core_gaps:
            lines.append("| Indicator | Area | Level | Description |")
            lines.append("|---|---|---|---|")
            for c in core_gaps:
                info = indicators[c]
                desc = info["description"][:90].replace("|", "\\|")
                lines.append(f"| {c} | {info['area']} | {info['level'] or '—'} | {desc} |")
        else:
            lines.append("_No uncovered core indicators — full coverage._")
        if ctso_codes:
            lines.append("")
            lines.append(
                f"_CTSO area {ctso}: {len(ctso_covered)}/{len(ctso_codes)} tagged "
                "(co-curricular via FBLA; not counted as a core gap)._"
            )
        sections.append("\n".join(lines))

    # DGD is a two-year sequence sharing ONE standards doc, so the pathway total is
    # scored against both levels at once. DGD II is void (see VOID_COURSES), so only
    # DGD I contributes — the L2-only indicators the bridge would have covered are
    # simply untaught until the 2027-28 DGD II exists. Do not restore a combined
    # "DGD I + II" row unless that course is actually running.
    dgd_std = enumerate_indicators(COURSES["dgd_i"][2])
    dgd_core = {c for c in dgd_std if not c.startswith("1.")}
    dgd_taught = covered_codes(COURSES["dgd_i"][1]) & dgd_core
    rows.append(
        f"| **DGD pathway (two-year)** | **{len(dgd_taught)}/{len(dgd_core)}** | "
        f"**{pct(len(dgd_taught), len(dgd_core))}** | {len(dgd_core) - len(dgd_taught)} | — | — |"
    )

    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    out = [
        "# Standards Coverage — All Courses",
        "",
        f"> Generated {ts} by `reports/compile_coverage_overview.py` from the "
        "grounded crosswalk JSON. Coverage is scored against **in-scope** "
        "indicators — those whose level tag includes the course's level (L1 for "
        "ACS I / WDD I / DGD I). Out-of-level "
        "(L2/Complementary in an L1 course) and the CTSO/FBLA area (1.0) are "
        "reported separately, not counted against coverage. Mechanical coverage "
        "from unit-level tags — see `acs1_standards_gap_status.md` / "
        "`wdd_standards_gap_status.md` for finer scope judgment.",
        "",
        "> **DGD is a two-year sequence sharing one standards document**, so the "
        "pathway row is scored against both levels at once (158 indicators). Only "
        "DGD I is taught: the DGD II bridge had no period on the 2026-27 master "
        "schedule and was superseded before it ran, so the L2-only indicators it "
        "would have covered are currently untaught. A DGD II built fresh for "
        "2027-28 will close them.",
        "",
        "## Summary",
        "",
        "| Course | In-scope covered | In-scope % | Gaps | Out-of-level | CTSO (1.0) tagged |",
        "|---|---|---|---|---|---|",
        *rows,
        "",
        "## Gap detail by course",
        "",
        *[s + "\n" for s in sections],
    ]
    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {OUT}")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
