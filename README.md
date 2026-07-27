# Curriculum Portfolio & Standards Crosswalk Auditor

Live: **https://willbumgardner.com/curriculum-portfolio/**

An interactive tool I built to answer a question I kept asking by hand: *do my courses actually cover the state standards they claim to?* It parses my real, day-by-day lesson plans, joins them against the parsed Nevada CTE standards catalog, and reports genuine coverage gaps while filtering out indicators that are out of scope for the course level.

I built it because I had the problem. After it surfaced the gaps, I rebuilt a 17-unit course around what the data showed.

## What it does

- **Crosswalk auditor** (`crosswalk.html`) — pick a course, see every standard indicator tagged *covered*, *gap*, or *out of scope*, traced back to the specific unit and day that teaches it.
- **Curriculum browser** (`curriculum.html`) — unit-by-unit view of each course map.
- **Five courses audited** — Advanced CS I, Web Design & Development, Digital Game Development I & II, and an intro CS course (CET), each mapped against its own grounded standards catalog.
- **Scope-aware gap logic** — an indicator counts as a gap only if it is uncovered *and* in-level for the course. Higher-level (L2) and complementary indicators are shown as out-of-scope rather than inflating the gap count.

## How it's built

- **Front end:** vanilla HTML/CSS/JS, no framework. Each view fetches grounded JSON from `reports/` and renders the crosswalk client-side.
- **Data pipeline (Python):** per-course compilers in `reports/` parse two sources into grounded JSON:
  - the standards catalog (parsed from the official Nevada CTE standards text, with page-furniture and level markers handled so L1/L2 indicators classify correctly), and
  - the course map (extracted from the `## Standards` sections of each day's lesson-plan file).
- **Source of truth:** the lesson plans themselves. Regenerate data after editing any plan, then the site reflects it.
- **Deploy:** GitHub Pages at a custom domain.

## Data regeneration

```bash
# Advanced CS I (and shared NV catalog)
python3 reports/fix_parsers.py
# Other courses have dedicated compilers:
python3 reports/compile_dgd_data.py       # Digital Game Development I
python3 reports/compile_dgd2_data.py      # Digital Game Development II
python3 reports/compile_cet_data.py       # Intro CS (CET)
python3 reports/compile_wdd_standards.py  # Web Design & Development — catalog
python3 reports/regen_wdd_course_map.py   # Web Design & Development — course map
```

Every command above runs and reproduces the committed JSON byte-for-byte. WDD is
split across two scripts because its course-map extractor was replaced:
`regen_wdd_course_map.py` expands code ranges and reads bare-code shorthand, which
the original missed, so the original invented phantom gaps. Only the catalog half
of the old `compile_wdd_data.py` survives, as `compile_wdd_standards.py`.

Every compiler validates before it writes and **refuses to publish broken data**,
so a regeneration either produces something the site can render or leaves the
previous file untouched. Check the committed data at any time:

```bash
python3 reports/validate_data.py        # exit 1 if anything would break the site
```

Errors block a write; warnings are printed but do not. The line is whether the
site reads the field. A day tag missing from the catalog is an error, because
`indexData()` in `crosswalk.js` drops it silently and the published coverage
percentage quietly drops with it. Junk in a course map's top-level `standards`
description map is a warning, because nothing renders it.

`reports/cet_standards.txt` is a **reconstructed** source. The original text dump of
Appendix A of the NDE CET Support Document (Aug 2023) was never committed, so the
CET compiler had no input. The file was rebuilt from
`cet_cs_standards_grounded.json`, the catalog that dump had already produced, and
the round trip is byte-identical — but its grounding is that JSON, not a fresh read
of the PDF. Re-dump the PDF if the standards are ever revised.

`compile_dgd_data.py` reads the DGD I lesson files through `dgd_lessons.py`, which
parses the daily-pacing headings:

```
## WEEK 1 · SESSION 1 (MON, 40 min) — Course Overview & What You'll Build
## WEEK 1 · FRIDAY 1 (FRI, 50 min) — Non-Digital Game Reflection
```

`day` is the meeting's position in the unit, not its `SESSION`/`FRIDAY` label.
Those two sequences are numbered independently — SESSION numbers run continuously
across a unit while FRIDAY numbers restart at 1 — so the labels collide and cannot
serve as day numbers. Document order also matches what "Day N" means everywhere
else in the vault.

`compile_dgd2_data.py` still splits on `## DAY` / `## FRIDAY`, which is correct:
the DGD II bridge files were never re-paced and still use that format.

## Run locally

```bash
python3 -m http.server   # then open http://localhost:8000
```

The front end fetches `reports/*.json` over relative paths, so it needs to be served, not opened from `file://`.

## Why this exists

I'm a CS teacher who builds the tools I wish I had. This one turned a tedious manual audit into something I trust, and it doubles as evidence of how I work: find the gap, build the thing, ground it in real data, iterate against real use.
