#!/usr/bin/env python3
"""Regenerate wdd_course_map_grounded.json from the WDD I lesson files.

Gemini's original extractor undercounted (missed bare-code shorthand), producing
phantom gaps. WDD lessons live in `03_Teaching/WDD_I/Unit_N/Redesign_Lessons.md`,
organized as `## SESSION N` / `## FRIDAY N` blocks each carrying a
`**Standards:** WDD x.x.x, y.y.y, a.a.a-b.b.b` line. Each block becomes a "day".
Ranges are expanded; only codes in the standards catalog are kept (no false positives).
"""
import json, re, pathlib

REPORTS = pathlib.Path(__file__).parent
WDD_DIR = REPORTS.parent.parent / "03_Teaching" / "WDD_I"  # reports/ now under Portfolio_Site/
CATALOG = json.loads((REPORTS / "wdd_cs_standards_grounded.json").read_text())

VALID = {}
for cs in CATALOG.values():
    for ps in cs["performance_standards"].values():
        for code, ind in ps["indicators"].items():
            VALID[code] = ind["description"]

SESSION_RE = re.compile(r"^##\s+(.*)$")
STD_LINE_RE = re.compile(r"\*\*Standards:\*\*\s*(.*)$")
RANGE_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)\s*[–-]\s*(?:\d+\.\d+\.)?(\d+)")
CODE_RE = re.compile(r"\d+\.\d+\.\d+")
TITLE_PREFIX_RE = re.compile(r"^(SESSION|FRIDAY|DAY|WEEK)\s*\d*\s*[—–:-]*\s*", re.IGNORECASE)


def codes_from_line(text: str):
    """Extract valid catalog codes from a Standards line, expanding ranges."""
    found = []

    def keep(code):
        if code in VALID and code not in found:
            found.append(code)

    # ranges first (e.g. "2.4.1-2.4.3"), then remove them so singletons don't double-count
    remainder = text
    for a, b, c, d in RANGE_RE.findall(text):
        for last in range(int(c), int(d) + 1):
            keep(f"{a}.{b}.{last}")
    remainder = RANGE_RE.sub(" ", remainder)
    for code in CODE_RE.findall(remainder):
        keep(code)
    return found


def unit_title(num: int, text: str) -> str:
    m = re.search(rf"#\s*Unit\s*{num}\s*[:—–-]*\s*(.+)$", text, re.MULTILINE)
    if not m:
        return f"Unit {num}"
    return re.sub(r"\s*[—–-]\s*Lesson Plans\s*$", "", m.group(1)).strip()


def build_unit(num: int):
    path = WDD_DIR / f"Unit_{num}" / "Redesign_Lessons.md"
    if not path.exists():
        return None
    text = path.read_text()
    lines = text.splitlines()
    days, cur_title, cur_codes, day_no = [], None, [], 0

    def flush():
        nonlocal cur_title, cur_codes, day_no
        if cur_title is not None:
            day_no += 1
            days.append({"day": day_no, "title": cur_title, "standards": cur_codes})
        cur_title, cur_codes = None, []

    for line in lines:
        if (m := SESSION_RE.match(line)):
            flush()
            cur_title = TITLE_PREFIX_RE.sub("", m.group(1).strip()).strip()
        elif cur_title is not None and (m := STD_LINE_RE.search(line)):
            cur_codes = codes_from_line(m.group(1))
    flush()

    unit_codes = sorted({c for d in days for c in d["standards"]})
    return {"number": num, "title": unit_title(num, text),
            "days": days, "standards": unit_codes}


if __name__ == "__main__":
    units = [u for n in range(1, 7) if (u := build_unit(n))]
    out = {"units": units, "standards": dict(sorted(VALID.items()))}
    (REPORTS / "wdd_course_map_grounded.json").write_text(json.dumps(out, indent=1))

    mapped = {c for u in units for d in u["days"] for c in d["standards"]}
    gaps = [c for c in VALID if c not in mapped and not c.startswith("1.")]
    print(f"units: {len(units)} | sessions: {sum(len(u['days']) for u in units)}")
    print(f"mapped codes: {len(mapped)} / {len(VALID)}")
    print(f"gaps (excl CTSO 1.0): {len(gaps)}")
