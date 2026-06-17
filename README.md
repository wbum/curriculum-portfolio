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
python3 reports/compile_dgd_data.py     # Digital Game Development I
python3 reports/compile_dgd2_data.py    # Digital Game Development II
python3 reports/compile_cet_data.py     # Intro CS (CET)
python3 reports/regen_wdd_course_map.py # Web Design & Development
```

## Run locally

```bash
python3 -m http.server   # then open http://localhost:8000
```

The front end fetches `reports/*.json` over relative paths, so it needs to be served, not opened from `file://`.

## Why this exists

I'm a CS teacher who builds the tools I wish I had. This one turned a tedious manual audit into something I trust, and it doubles as evidence of how I work: find the gap, build the thing, ground it in real data, iterate against real use.
