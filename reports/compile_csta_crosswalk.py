#!/usr/bin/env python3
"""Roll the four per-course CSTA 2026 crosswalks up into one cross-course view.

The per-course crosswalks in 03_Teaching are the source of truth. Each was
verified against course overviews and day plans when it was written; nothing
here re-judges them. This script only aggregates:

    03_Teaching/ACS_I/ACS_I_CSTA_2026_Crosswalk.md
    03_Teaching/WDD_I/WDD_I_CSTA_2026_Crosswalk.md
    03_Teaching/DGD_I/DGD_I_CSTA_2026_Crosswalk.md
    03_Teaching/CET/CET_CSTA_2026_Crosswalk.md

plus csta2026_standards_grounded.json for the standard text and band, so the
roll-up names standards no course table happens to list.

Writes csta2026-coverage.md and csta2026_coverage_grounded.json.

Scoping matters here. The 2026 framework splits Foundational (what every
graduate should know -- 46 standards at HS) from Specialty (optional deepening,
S1/S2 -- 135 standards). A foundational course is not expected to cover
Specialty standards, so Foundational and Specialty are reported separately and
never summed. Reporting one number over all 181 would misread by design.
"""
import argparse
import json
import pathlib
import re
from collections import Counter, defaultdict

REPORTS = pathlib.Path(__file__).parent
VAULT = REPORTS.parent.parent
TEACHING = VAULT / "03_Teaching"
CATALOG = REPORTS / "csta2026_standards_grounded.json"
OUT_MD = REPORTS / "csta2026-coverage.md"
OUT_JSON = REPORTS / "csta2026_coverage_grounded.json"

COURSES = {
    "acs_i": ("Advanced Computer Science I", "ACS_I/ACS_I_CSTA_2026_Crosswalk.md"),
    "wdd_i": ("Web Design & Development I", "WDD_I/WDD_I_CSTA_2026_Crosswalk.md"),
    "dgd_i": ("Digital Game Development I", "DGD_I/DGD_I_CSTA_2026_Crosswalk.md"),
    "cet": ("Computer Engineering Technology", "CET/CET_CSTA_2026_Crosswalk.md"),
}

# ✓ taught explicitly, ◐ touched but not to full depth, ✗ not addressed.
GLYPH = {"✓": "covered", "◐": "partial", "✗": "gap"}
RANK = {"covered": 3, "partial": 2, "gap": 1, "unclaimed": 0}
CODE_RE = re.compile(r"^`?((?:HS|S[12])-[A-Z]{3}-[A-Z]{2}-\d{2})`?$")


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_crosswalk(path: pathlib.Path) -> tuple[dict, dict]:
    """Return (code -> {status, note}, frontmatter).

    Only tables whose header carries a "Status" column are read. That
    deliberately skips ACS I's partials drill-down table, whose columns are
    First pass / Verified -- its conclusions are already folded into the
    concept tables, and reading both would double-count.
    """
    text = path.read_text()
    front = dict(re.findall(r"^(\w+):\s*(.+)$", text.split("---")[1], re.M)) \
        if text.startswith("---") else {}

    rows: dict[str, dict] = {}
    status_col = note_col = None
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            status_col = None
            continue
        c = cells(line)
        lowered = [x.lower() for x in c]
        if "status" in lowered:
            status_col = lowered.index("status")
            note_col = len(c) - 1
            continue
        if status_col is None or status_col >= len(c):
            continue
        if not (m := CODE_RE.match(c[0])):
            continue
        glyphs = [g for g in c[status_col] if g in GLYPH]
        if not glyphs:
            continue
        rows[m.group(1)] = {
            "status": GLYPH[glyphs[0]],
            "note": c[note_col] if note_col < len(c) else "",
        }
    return rows, front


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    raw = json.loads(CATALOG.read_text())
    standards, concept_titles = {}, {}
    for concept_code, concept in raw.items():
        concept_titles[concept_code] = concept["title"]
        for sub in concept["performance_standards"].values():
            for code, ind in sub["indicators"].items():
                if ind["level"] in ("HS", "S1", "S2"):
                    standards[code] = {
                        "concept": concept_code,
                        "band": ind["level"],
                        "tier": "Foundational" if ind["level"] == "HS" else "Specialty",
                        "description": ind["description"],
                    }

    per_course, fronts, unknown = {}, {}, []
    for key, (title, rel) in COURSES.items():
        rows, front = parse_crosswalk(TEACHING / rel)
        unknown += [(key, c) for c in rows if c not in standards]
        per_course[key] = {c: v for c, v in rows.items() if c in standards}
        fronts[key] = front
        counts = Counter(v["status"] for v in per_course[key].values())
        print(f"{title}: {len(per_course[key])} rows  "
              f"covered={counts['covered']} partial={counts['partial']} gap={counts['gap']}")

    coverage = {}
    for code, meta in standards.items():
        best, by = "unclaimed", {}
        for key, rows in per_course.items():
            if code in rows:
                by[key] = rows[code]["status"]
                if RANK[rows[code]["status"]] > RANK[best]:
                    best = rows[code]["status"]
        coverage[code] = {**meta, "status": best, "by_course": by}

    if unknown:
        print(f"WARNING: {len(unknown)} codes not in catalog: {unknown[:5]}")

    if args.dry_run:
        print("--dry-run: nothing written")
        return

    OUT_MD.write_text(render(coverage, concept_titles, per_course, fronts, unknown))
    OUT_JSON.write_text(json.dumps(
        {"coverage": coverage, "per_course": per_course}, indent=1) + "\n")
    print(f"\nwrote {OUT_MD.name} and {OUT_JSON.name}")


def tier_table(coverage: dict, concept_titles: dict, tier: str) -> list[str]:
    by_concept: dict[str, Counter] = defaultdict(Counter)
    for v in coverage.values():
        if v["tier"] == tier:
            by_concept[v["concept"]][v["status"]] += 1
    out = ["| Concept | Standards | Covered | Partial | Not addressed |",
           "|---|---:|---:|---:|---:|"]
    tot = Counter()
    for code in sorted(by_concept, key=lambda c: -sum(by_concept[c].values())):
        c = by_concept[code]
        n = sum(c.values())
        tot.update(c)
        out.append(f"| {concept_titles[code]} (`{code}`) | {n} | {c['covered']} "
                   f"| {c['partial']} | {c['gap'] + c['unclaimed']} |")
    n = sum(tot.values())
    out.append(f"| **Total** | **{n}** | **{tot['covered']}** | **{tot['partial']}** "
               f"| **{tot['gap'] + tot['unclaimed']}** |")
    return out


def render(coverage, concept_titles, per_course, fronts, unknown) -> str:
    L, A = [], None
    A = L.append
    A("# Four Courses vs. the 2026 CSTA PK–12 Standards — Cross-Course Roll-Up")
    A("")
    A("Aggregates the four per-course CSTA 2026 crosswalks in `03_Teaching`. Those "
      "documents are the source of truth and were each verified against course "
      "overviews and day plans; this roll-up does not re-judge any status, it only "
      "combines them and adds the standards no course table lists.")
    A("")
    A("**Foundational and Specialty are reported separately and never summed.** The "
      "2026 framework treats Foundational (46 standards at HS) as what every graduate "
      "should know, and Specialty (S1/S2) as optional deepening. A foundational course "
      "is not expected to cover Specialty standards, so a single percentage across all "
      "181 would misstate the picture by design.")
    A("")

    found = {k: v for k, v in coverage.items() if v["tier"] == "Foundational"}
    c = Counter(v["status"] for v in found.values())
    reached = c["covered"] + c["partial"]
    A("## Foundational band (HS) — the band that matters")
    A("")
    A(f"- **{c['covered']} of {len(found)}** covered outright by at least one course "
      f"({c['covered'] / len(found):.0%})")
    A(f"- **{reached} of {len(found)}** reached at least partially "
      f"({reached / len(found):.0%})")
    A(f"- **{len(found) - reached}** not addressed by any of the four courses")
    A("")
    L.extend(tier_table(coverage, concept_titles, "Foundational"))
    A("")

    A("### Foundational standards no course reaches")
    A("")
    holes = sorted(k for k, v in found.items() if v["status"] in ("gap", "unclaimed"))
    if not holes:
        A("None. Every HS-Foundational standard is reached by at least one course.")
    else:
        for code in holes:
            v = found[code]
            marked = sorted(c for c, s in v["by_course"].items() if s == "gap")
            who = (f"explicitly marked ✗ by: {', '.join(marked)}" if marked
                   else "not listed in any crosswalk")
            A(f"- `{code}` {v['description']}  \n  *({who})*")
    A("")

    A("## Specialty bands (S1/S2) — optional deepening")
    A("")
    A("Each course targets at most one specialty area. Coverage outside a course's own "
      "area is expected to be empty and is not a finding.")
    A("")
    L.extend(tier_table(coverage, concept_titles, "Specialty"))
    A("")

    A("## Per course")
    A("")
    A("| Course | Rows | Covered | Partial | Gap | Crosswalk written | Verification |")
    A("|---|---:|---:|---:|---:|---|---|")
    for key, (title, rel) in COURSES.items():
        rows = per_course[key]
        cc = Counter(v["status"] for v in rows.values())
        f = fronts.get(key, {})
        status = f.get("status", "")
        status = (status[:76] + "…") if len(status) > 78 else status
        A(f"| {title} | {len(rows)} | {cc['covered']} | {cc['partial']} | {cc['gap']} "
          f"| {f.get('generated', '?')} | {status} |")
    A("")

    A("## Where the four courses overlap")
    A("")
    A("Foundational standards reached by three or more courses — the spine the "
      "pathway repeats, which is worth knowing before adding anything new.")
    A("")
    multi = sorted(
        ((k, v) for k, v in found.items()
         if sum(1 for s in v["by_course"].values() if s in ("covered", "partial")) >= 3),
        key=lambda kv: -sum(1 for s in kv[1]["by_course"].values()
                            if s in ("covered", "partial")))
    for code, v in multi:
        hits = [c for c, s in v["by_course"].items() if s in ("covered", "partial")]
        A(f"- `{code}` ({len(hits)} courses: {', '.join(sorted(hits))}) "
          f"{v['description'][:100]}")
    A("")

    if unknown:
        A("## Codes in a crosswalk that are not in the parsed catalog")
        A("")
        for key, code in unknown:
            A(f"- `{code}` in {COURSES[key][0]}")
        A("")

    A("## Provenance")
    A("")
    A("- Standards catalog parsed from the official PDF by `parse_csta2026.py` "
      "(331 standards; 46 at HS-Foundational, matching each course crosswalk's own "
      "scope count).")
    A("- Per-course statuses read verbatim from the four crosswalks. Legend as used "
      "there: ✓ taught explicitly · ◐ touched but not to the standard's full depth · "
      "✗ not addressed.")
    A("- DGD II is excluded: the 26–27 bridge build was voided.")
    A("")
    A("Standards text © 2026 Computer Science Teachers Association, CC BY-NC-SA 4.0, "
      "<https://csteachers.org/pk12standards/>.")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
