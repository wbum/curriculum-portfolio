#!/usr/bin/env python3
"""Parse the 2026 CSTA PK-12 Computer Science Standards into a grounded catalog.

Source: the official PDF, extracted with layout preserved:

    pdftotext -layout 2026-CSTA-PK-12-Computer-Science-Standards.pdf csta2026_standards.txt

CSTA publishes no machine-readable release for the 2026 standards -- the
downloads pages under /k12standards/ and /pk12standards/ both serve the separate
2020 *Standards for CS Teachers* PDFs -- so the PDF is the only source.
Licensed CC BY-NC-SA 4.0 (https://csteachers.org/pk12standards/).

Shape
-----
The site's catalog format is a three-level tree (strand -> performance standard
-> indicator). CSTA 2026 is also three levels, so the concepts map onto it
without extending the schema that validate_data.py and crosswalk.js already
enforce:

    concept (ALG)  ->  strand
    subconcept (PS)  ->  performance standard
    standard (HS-ALG-PS-01)  ->  indicator

`level` carries the grade band (EK, E1-E5, MS, HS, S1, S2). That slot holds
Nevada's L1/L2/C tags in the other catalogs and means the same thing here:
which population the standard applies to. The 2026-only fields (boundary
statement, practices, dispositions) ride along on the indicator; the validator
ignores unknown keys and the site renders `description`.

Identifiers changed completely in 2026. The 2017-era codes (3A-AP-13) do not
appear in this document at all, so nothing joins to a pre-2026 alignment.
"""
import argparse
import json
import pathlib
import re
from collections import Counter

from validate_data import write_json_validated

REPORTS = pathlib.Path(__file__).parent
DEFAULT_TXT = REPORTS / "csta2026_standards.txt"
DEFAULT_OUT = REPORTS / "csta2026_standards_grounded.json"

# Concept and subconcept names, transcribed from the naming-convention tables in
# the source PDF ("Foundational Standards for PK-12" and "High School Specialty
# Standards"). Transcribed rather than parsed: both tables are multi-column
# layouts with names wrapped across lines ("Artificial / Intelligence"), which
# pdftotext splits unpredictably, and the legend is fixed for the life of the
# 2026 edition.
#
# Subconcept abbreviations are NOT globally unique -- IM is three different
# things (Impacts of Algorithms & Design, of Data Science, of Computing
# Systems), and DD/PP/TR recur across specialty areas -- so they are keyed by
# (concept, subconcept), never by subconcept alone.
CONCEPTS = {
    # Foundational (EK-E5, MS, HS)
    "ALG": ("Algorithms & Design", {
        "PS": "Algorithmic Problem Solving",
        "ML": "Machine Learning",
        "IM": "Impacts of Algorithms & Design",
    }),
    "PRO": ("Programming", {
        "PD": "Program Development",
        "VD": "Variables & Data Storage",
        "RD": "Reading & Documenting",
        "TR": "Testing & Refining",
    }),
    "DAT": ("Data & Analysis", {
        "DC": "Data Collection & Preparation",
        "DI": "Data Investigation",
        "IM": "Impacts of Data Science",
    }),
    "SYS": ("Systems & Security", {
        "HW": "Hardware & Software",
        "SE": "Security",
        "NT": "Networks",
        "IM": "Impacts of Computing Systems",
    }),
    "SOC": ("Computing & Society", {
        "HI": "History of Computing",
        "ET": "Emerging Technologies",
        "HU": "Humans & Computing",
        "CE": "Career Exploration",
    }),
    # Specialty (S1, S2)
    "AIN": ("Artificial Intelligence", {
        "DD": "Design & Development",
        "DS": "Data Science for AI",
        "HR": "Human Responsibility",
        "PP": "Professional Practice",
    }),
    "CYB": ("Cybersecurity", {
        "ND": "Network Theory & Design",
        "NO": "Network Operations",
        "TS": "Threats & Security Measures",
        "CP": "Cybersecurity Policies",
        "PP": "Professional Practice",
    }),
    "DSC": ("Data Science", {
        "CC": "Creation & Curation",
        "AM": "Analysis & Modeling Techniques",
        "MI": "Model Interpretation & Reasoning",
        "VZ": "Visualization",
        "PP": "Professional Practice",
    }),
    "GMD": ("Game Development", {
        "DD": "Design & Development",
        "PX": "Player Experience",
        "AR": "Architecture",
        "PP": "Professional Practice",
    }),
    "PHY": ("Physical Computing", {
        "HC": "Hardware & Circuit Design",
        "IO": "Inputs & Outputs",
        "DD": "Design & Development",
        "CI": "Connectivity & Internet of Things",
        "PP": "Professional Practice",
    }),
    "SWD": ("Software Development", {
        "DD": "Design & Development",
        "UX": "User Experience",
        "TR": "Testing & Refining",
        "PP": "Professional Practice",
    }),
    "XCS": ("X+CS", {"XC": "X+CS"}),
}

BANDS = ("EK", "E1", "E2", "E3", "E4", "E5", "MS", "HS", "S1", "S2")

CODE = r"(EK|E[1-5]|MS|HS|S[12])-([A-Z]{3})-([A-Z]{2})-(\d{2})"
DEF_RE = re.compile(rf"^\s*{CODE}:\s*(.*)$")
BOUNDARY_RE = re.compile(r"^\s*Boundary Statement:\s*(.*)$")
# Practices and dispositions share one line, laid out as two columns.
PRACTICE_RE = re.compile(
    r"^\s*Practice\(s\):\s*(.*?)\s{2,}Disposition\(s\):\s*(.*)$"
)

# Running headers, page footers, and the bare concept abbreviations that the
# PDF prints in the outer margin of every standards page. None of these are
# content, and all of them land mid-record where a continuation line would.
NOISE_RE = re.compile(
    r"^\s*(?:"
    r"©\s*\d{4}\s*Computer Science Teachers Association"
    r"|(?:Foundational Standards|High School Specialty Standards|Specialty Standards)\b"
    r"|\d+\s*$"
    r"|(?:" + "|".join(CONCEPTS) + r")\s*$"
    r"|(?:" + "|".join(BANDS) + r")\s*$"
    r")"
)


def _is_noise(line: str) -> bool:
    return not line.strip() or bool(NOISE_RE.match(line))


def parse(txt_path: pathlib.Path) -> tuple[dict, dict]:
    """Return (records by code, duplicate counter).

    A standard's identifier appears in the body once with its full entry and
    again in the progression charts, which repeat the code and statement with no
    boundary statement. Records are kept only if they carry a boundary
    statement, so the chart repeats never overwrite the real entry.
    """
    lines = txt_path.read_text().splitlines()
    records: dict[str, dict] = {}
    dupes: Counter = Counter()

    i, n = 0, len(lines)
    while i < n:
        if not (m := DEF_RE.match(lines[i])):
            i += 1
            continue

        band, concept, sub, num, head = m.groups()
        code = f"{band}-{concept}-{sub}-{num}"
        statement = [head.strip()]
        boundary: list[str] = []
        practices = dispositions = ""

        i += 1
        target = statement
        while i < n:
            line = lines[i]
            if DEF_RE.match(line):
                break  # next standard begins
            if (b := BOUNDARY_RE.match(line)):
                boundary.append(b.group(1).strip())
                target = boundary
                i += 1
                continue
            if (p := PRACTICE_RE.match(line)):
                practices, dispositions = p.group(1).strip(), p.group(2).strip()
                i += 1
                break  # practices close the record
            if not _is_noise(line):
                target.append(line.strip())
            i += 1

        record = {
            "code": code,
            "band": band,
            "concept": concept,
            "subconcept": sub,
            "description": " ".join(s for s in statement if s).strip(),
            "boundary_statement": " ".join(b for b in boundary if b).strip(),
            "practices": [p.strip() for p in practices.split(",") if p.strip()],
            "dispositions": [d.strip() for d in dispositions.split(",") if d.strip()],
        }

        if code in records:
            dupes[code] += 1
            # Keep whichever record actually carries a boundary statement; the
            # progression charts repeat the code and statement without one.
            if not record["boundary_statement"]:
                continue
            if records[code]["boundary_statement"]:
                continue
        records[code] = record

    return records, dupes


def build_catalog(records: dict) -> dict:
    """Coerce records into the site's three-level catalog shape."""
    catalog: dict = {}
    for code in sorted(records):
        rec = records[code]
        concept, sub = rec["concept"], rec["subconcept"]
        concept_title, subs = CONCEPTS.get(concept, (concept, {}))

        strand = catalog.setdefault(
            concept, {"title": concept_title, "performance_standards": {}}
        )
        perf = strand["performance_standards"].setdefault(
            sub, {"title": subs.get(sub, sub), "indicators": {}}
        )
        perf["indicators"][code] = {
            "description": rec["description"],
            "level": rec["band"],
            "boundary_statement": rec["boundary_statement"],
            "practices": rec["practices"],
            "dispositions": rec["dispositions"],
        }
    return catalog


def report(records: dict, dupes: Counter) -> None:
    bands = Counter(r["band"] for r in records.values())
    print(f"standards parsed: {len(records)}")
    print("by band:", " ".join(f"{b}={bands[b]}" for b in BANDS if bands[b]))

    hs = {c: r for c, r in records.items() if r["band"] in ("HS", "S1", "S2")}
    by_concept = Counter(r["concept"] for r in hs.values())
    print(f"\nHS + specialty (Will's slice): {len(hs)}")
    for concept, count in by_concept.most_common():
        print(f"  {concept}  {CONCEPTS.get(concept, (concept,))[0]:<26} {count}")

    missing_desc = [c for c, r in records.items() if not r["description"]]
    missing_bound = [c for c, r in records.items() if not r["boundary_statement"]]
    unknown = sorted({
        (r["concept"], r["subconcept"]) for r in records.values()
        if r["subconcept"] not in CONCEPTS.get(r["concept"], (None, {}))[1]
    })
    print(f"\nempty descriptions: {len(missing_desc)} {missing_desc[:5]}")
    print(f"empty boundary statements: {len(missing_bound)} {missing_bound[:5]}")
    print(f"unknown concept/subconcept pairs: {unknown or 'none'}")
    print(f"codes seen more than once: {len(dupes)} (progression charts)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--txt", type=pathlib.Path, default=DEFAULT_TXT)
    ap.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true",
                    help="parse and report without writing the catalog")
    args = ap.parse_args()

    records, dupes = parse(args.txt)
    report(records, dupes)

    if args.dry_run:
        print("\n--dry-run: nothing written")
        return

    catalog = build_catalog(records)
    write_json_validated(args.out, catalog, "catalog", indent=1)
    print(f"\nwrote {args.out.name}: {len(catalog)} concepts")


if __name__ == "__main__":
    main()
