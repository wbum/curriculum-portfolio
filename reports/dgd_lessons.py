"""Parse DGD I lesson files into class meetings.

The unit files were re-paced from blocks to a daily schedule, and their headings
changed with it:

    old:  ## DAY 1 — Course Overview
          ## FRIDAY 1 — Non-Digital Game Reflection

    new:  ## WEEK 1 · SESSION 1 (MON, 40 min) — Course Overview & What You'll Build
          ## WEEK 1 · FRIDAY 1 (FRI, 50 min) — Non-Digital Game Reflection

`compile_dgd_data.py` split on the old shape, so after the re-pace it matched
nothing and produced eight units with zero days. Validation caught that before it
published; this module is the fix.

Two things about the new format matter for numbering:

- SESSION numbers run continuously across a unit (1..12 in Unit 1), while FRIDAY
  numbers restart at 1. So SESSION 1 and FRIDAY 1 both claim "1" and the labels
  cannot be used as day numbers directly.
- A Friday falls between SESSION 4 and SESSION 5 in the week.

So `day` is the meeting's position in document order, which is what "Day N" means
everywhere else in the vault and what the crosswalk renders. The session label
itself is not carried through: a standards crosswalk cares which meeting covers an
indicator, not whether it ran 40 or 50 minutes.
"""
from __future__ import annotations

import re
from pathlib import Path

LESSONS_DIR = Path(__file__).parent.parent.parent / "03_Teaching" / "DGD_I"

# "## WEEK 1 · SESSION 1 (MON, 40 min) — Title". The separator after WEEK n is a
# middle dot in the files; accept a bullet too so a copy-paste variant still reads.
# The time parenthetical and the dash are optional so a lightly-formatted heading
# still counts as a meeting rather than silently vanishing.
MEETING_RE = re.compile(
    r"^##[ \t]+WEEK[ \t]+(?P<week>\d+)[ \t]*[·•][ \t]*"
    r"(?P<kind>SESSION|FRIDAY)[ \t]+(?P<label>\d+)[ \t]*"
    r"(?:\((?P<meta>[^)]*)\))?[ \t]*"
    r"(?:[—–:-][ \t]*(?P<title>.*?))?[ \t]*$",
    re.MULTILINE,
)

UNIT_H1_RE = re.compile(r"^#[ \t]+(?P<title>.+?)[ \t]*$", re.MULTILINE)

# Codes appear as "DGD.1.1.1" or "DGD 1.1.1"; the site indexes them bare.
STANDARD_RE = re.compile(r"DGD[.\s]+(\d+\.\d+\.\d+)")

# The "**Standards:**" line sits directly under the heading. Scan a few lines so a
# blank line or a stray note does not lose it, but stop well short of the next
# heading so one meeting cannot inherit another's standards.
STANDARDS_SCAN_LINES = 3


def parse_unit_title(content: str) -> str:
    """Unit title from the H1, minus the 'Unit N:' prefix and 'Lesson Plans' tail."""
    m = UNIT_H1_RE.search(content)
    if not m:
        return ""
    title = re.sub(r"^Unit[ \t]+\d+:[ \t]*", "", m.group("title"))
    title = re.sub(r"[ \t]*[—–-][ \t]*Lesson Plans[ \t]*$", "", title)
    return title.strip()


def _standards_after(content: str, start: int, end: int) -> list[str]:
    window = content[start:end].splitlines()[:STANDARDS_SCAN_LINES]
    codes: list[str] = []
    for code in STANDARD_RE.findall("\n".join(window)):
        if code not in codes:
            codes.append(code)
    return codes


def parse_meetings(content: str) -> list[dict]:
    """Every class meeting in a unit file, in document order.

    `day` is the meeting's position in the unit, not its SESSION/FRIDAY label --
    those two sequences are numbered independently and would collide.
    """
    matches = list(MEETING_RE.finditer(content))
    meetings: list[dict] = []
    for index, match in enumerate(matches):
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        meetings.append(
            {
                "day": index + 1,
                "title": (match.group("title") or "").strip(),
                "standards": _standards_after(content, match.end(), body_end),
            }
        )
    return meetings


def unit_lesson_files(lessons_dir: Path | None = None) -> list[tuple[int, Path]]:
    """(unit number, lessons file) for every DGD I unit, in unit order."""
    lessons_dir = Path(lessons_dir or LESSONS_DIR)
    found: list[tuple[int, Path]] = []
    for entry in sorted(lessons_dir.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("Unit_"):
            continue
        try:
            number = int(entry.name.split("_")[1])
        except (IndexError, ValueError):
            continue
        path = entry / f"Unit_{number}_Lessons.md"
        if path.is_file():
            found.append((number, path))
    return sorted(found)


def parse_unit(number: int, path: Path) -> dict:
    """A unit entry in course-map shape."""
    content = path.read_text(encoding="utf-8")
    meetings = parse_meetings(content)
    unit_standards: list[str] = []
    for meeting in meetings:
        for code in meeting["standards"]:
            if code not in unit_standards:
                unit_standards.append(code)
    return {
        "number": number,
        "title": parse_unit_title(content) or f"Unit {number}",
        "days": meetings,
        "standards": unit_standards,
    }


def parse_units(lessons_dir: Path | None = None) -> list[dict]:
    return [parse_unit(n, p) for n, p in unit_lesson_files(lessons_dir)]
