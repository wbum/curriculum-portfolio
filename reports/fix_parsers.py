#!/usr/bin/env python3
"""Fix two parser bugs in the grounded datasets:
1. NV standard indicator descriptions truncated at line wraps.
2. ACS unit titles pulled from the document H1 instead of the real unit title.
Rewrites nv_cs_standards_grounded.json and acs1_course_map_grounded.json in place.
"""
import json, re, pathlib

REPORTS = pathlib.Path(__file__).parent
VAULT = REPORTS.parent.parent  # reports/ now lives under Portfolio_Site/
ACS_DIR = VAULT / "03_Teaching" / "ACS_I"

# ---------- Bug 1: NV standards full descriptions ----------
CS_RE = re.compile(r"^CONTENT STANDARD (\d+\.0):\s*(.+)$")
PS_RE = re.compile(r"^Performance Standard (\d+\.\d+):\s*(.+)$")
IND_RE = re.compile(r"^(\d+\.\d+\.\d+)\s+(.*)$")
LEVEL_TOKENS = ("L1", "L2", "C")


def normalize_level(paren_text: str) -> str:
    found = [t for t in LEVEL_TOKENS if re.search(rf"\b{re.escape(t)}\b", paren_text)]
    return ", ".join(found)


def split_desc_level(buf: str):
    """Trailing parenthetical holds the level tags; everything before is the description."""
    # Some indicators end with "(L2) Revised: 7/26/2023"; drop the trailing
    # "Revised: <date>" so the level parenthetical sits at the end of the string.
    buf = re.sub(r"\s*Revised:\s*\d{1,2}/\d{1,2}/\d{2,4}\s*$", "", buf)
    m = re.search(r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*$", buf)
    if not m:
        return buf.strip(), ""
    level = normalize_level(m.group(1))
    if not level:  # trailing parens were part of the description, not a level tag
        return buf.strip(), ""
    return buf[: m.start()].strip(), level


def parse_nv(txt_path=None, page_header="Advanced Computer Science Standards"):
    lines = pathlib.Path(txt_path or (REPORTS / "nv_cs_standards.txt")).read_text().splitlines()
    out, cur_cs, cur_ps, buf, target = {}, None, None, None, None

    def flush():
        nonlocal buf, target
        if target is not None and buf:
            desc, level = split_desc_level(buf)
            target["description"], target["level"] = desc, level
        buf, target = None, None

    for raw in lines:
        line = raw.strip()
        # Stop at the complementary-course back-matter so the last indicator (7.1.3)
        # doesn't absorb the trailing program boilerplate.
        if target is not None and re.search(r"Complementary Course|State Complementary Skill", line):
            flush()
            break
        if (m := CS_RE.match(line)):
            # The PDF appends a separate "Complementary Course Standards" program
            # that reuses keys 1.0/2.0/3.0. Stop at that boundary to avoid clobbering
            # the main Advanced CS Program of Study (1.0-7.0).
            if m.group(1) in out:
                break
            flush()
            cur_cs = m.group(1)
            out[cur_cs] = {"title": m.group(2).strip(), "performance_standards": {}}
            cur_ps = None
            continue
        if (m := PS_RE.match(line)):
            flush()
            cur_ps = m.group(1)
            if cur_cs:
                out[cur_cs]["performance_standards"][cur_ps] = {
                    "title": m.group(2).strip(), "indicators": {}
                }
            continue
        if cur_cs and cur_ps and (m := IND_RE.match(line)):
            flush()
            ind = m.group(1)
            target = {}
            out[cur_cs]["performance_standards"][cur_ps]["indicators"][ind] = target
            buf = m.group(2)
            continue
        # continuation line: skip page headers/footers/blank lines, else append
        if target is not None and line and page_header not in line \
                and "Nevada CTE" not in line and "Revised:" not in line \
                and not line.isdigit():
            buf += " " + line
    flush()
    return out


# ---------- Bug 2: real ACS unit titles ----------
UNIT_TITLE_RE = re.compile(r"\*\*Unit Title:\s*(.+?)\*\*")
H1_RE = re.compile(r"^#\s+(.+)$")
GENERIC = {"unit at a glance", "standards addressed", "the big picture",
           "learning objectives", "overview", "unit overview", "related files"}


def title_from_h1(num: int, h1: str) -> str:
    """Strip 'Unit N', 'Master Overview', and separators from the H1, leaving the title."""
    t = re.sub(rf"\bUnit\s+{num}\b", "", h1, count=1)
    t = re.sub(r"Master Overview", "", t, flags=re.IGNORECASE)
    return t.strip(" :—–-\t")


def unit_title(num: int) -> str:
    path = ACS_DIR / f"ACS1 Unit {num}" / f"Unit_{num}_Master_Overview.md"
    text = path.read_text()
    for line in text.splitlines():
        if (m := H1_RE.match(line.strip())):
            if (t := title_from_h1(num, m.group(1))):
                return t
            break  # H1 carried no title; fall through to other sources
    if (m := UNIT_TITLE_RE.search(text)):
        return m.group(1).strip()
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("## ") and s[3:].strip().lower() not in GENERIC:
            return s[3:].strip()
    return f"Unit {num}"


ADVCS_RE = re.compile(r"ADVCS\.\d+\.\d+\.\d+")
# Inside a standards section, codes may appear bare (shorthand lists like
# "ADVCS.5.3.2, 5.3.3"). Capture optional-prefix three-part codes there.
LOOSE_CODE_RE = re.compile(r"(?:ADVCS\.)?(\d+\.\d+\.\d+)")
HEADING_RE = re.compile(r"^#+\s+(.*)$")


def day_standards(num: int, day: int):
    """Re-extract ADVCS codes from a day's lesson plan (source of truth).

    Outside standards sections, only explicit ADVCS.x.x.x codes count (avoids
    false positives from prose). Inside a '## Standards' / '## Nevada Standards'
    section, bare x.x.x codes are also captured and normalized to the ADVCS prefix.
    """
    path = ACS_DIR / f"ACS1 Unit {num}" / f"Unit_{num}_Day_{day}_Lesson_Plan.md"
    if not path.exists():
        return None  # signal: keep existing
    seen = []

    def add(code: str):
        code = code if code.startswith("ADVCS.") else f"ADVCS.{code}"
        if code not in seen:
            seen.append(code)

    in_standards = False
    for line in path.read_text().splitlines():
        if (m := HEADING_RE.match(line)):
            in_standards = "standard" in m.group(1).lower()
            continue
        if in_standards:
            for code in LOOSE_CODE_RE.findall(line):
                add(code)
        else:
            for code in ADVCS_RE.findall(line):
                add(code)
    return seen


def fix_acs():
    data = json.loads((REPORTS / "acs1_course_map_grounded.json").read_text())
    for u in data["units"]:
        u["title"] = unit_title(u["number"])
        for d in u["days"]:
            stds = day_standards(u["number"], d["day"])
            if stds is not None:
                d["standards"] = stds
    return data


if __name__ == "__main__":
    nv = parse_nv()
    (REPORTS / "nv_cs_standards_grounded.json").write_text(json.dumps(nv, indent=1))
    acs = fix_acs()
    (REPORTS / "acs1_course_map_grounded.json").write_text(json.dumps(acs, indent=1))

    n = sum(len(ps["indicators"]) for cs in nv.values()
            for ps in cs["performance_standards"].values())
    trunc = [f"{cs}/{ps}/{i}" for cs, cv in nv.items()
             for ps, pv in cv["performance_standards"].items()
             for i, iv in pv["indicators"].items() if not iv["description"]]
    print(f"NV indicators: {n}")
    print(f"empty descriptions: {len(trunc)}")
    print("titles:", [u["title"] for u in acs["units"]])
