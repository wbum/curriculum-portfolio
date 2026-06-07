# WDD I — Standards Coverage Status

Source of truth: `03_Teaching/WDD_I/Unit_N/Redesign_Lessons.md` (`## SESSION`/`## FRIDAY`
blocks with `**Standards:**` lines). Regenerate with `python3 Portfolio_Site/reports/regen_wdd_course_map.py`.
Standards catalog: `python3 -c "import fix_parsers,json; json.dump(fix_parsers.parse_nv('wdd_standards.txt', page_header='Web Design and Development Standards'), open('wdd_cs_standards_grounded.json','w'), indent=1)"`.

## Coverage (Nevada Web Design & Development, Content Areas 1.0–7.0, 141 indicators)

| | |
|---|---|
| Mapped (taught) | 91 |
| Gaps excluding CTSO 1.0 | 43 |
| — of those, L2 / out-of-scope for L1 | 43 |
| — true L1 gaps | **0** |

**L1 coverage is complete.** Every L1 indicator (outside the by-design-excluded
CTSO Standard 1.0) is taught in the redesign. The 43 remaining gaps are all
L2/Complementary, not expected in an L1 course.

## Correction history
Gemini's original `wdd_course_map_grounded.json` undercounted (missed bare-code and
range shorthand), reporting **63 mapped / 65 gaps / 22 false L1 gaps**. All 22 were
taught-but-untagged (e.g. CSS 4.3.5, e-commerce 2.5.2, privacy law 3.2.6/3.2.7 in
Unit 4). Gemini's standards parser also mislabeled levels (5.5.3, 5.6.3 tagged L1
when they are L2) due to trailing `Revised:`/page-break pollution. Both regenerated
cleanly: 141 indicators, 0 mis-parsed levels, 91 mapped, 0 true L1 gaps.

## Notes
- WDD I excludes CTSO Standard 1.0 by design — not a gap (per project rule).
- Coverage = a catalog code appears in a session's `**Standards:**` line; ranges
  (`2.4.1–2.4.3`) expanded, 2-part PS codes (`2.5`) intentionally not expanded.
