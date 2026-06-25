# ACS I — Standards Coverage Status

Source of truth: `*_Day_*_Lesson_Plan.md` files. Regenerate the auditor data with
`python3 Portfolio_Site/reports/fix_parsers.py` after editing any lesson plan.

## Coverage (Nevada Advanced CS, Content Areas 1.0–7.0)

**Scored level-aware (2026-06-24): ACS I is an L1 course, so coverage is measured
against L1 indicators only. Out-of-level (L2/Complementary) indicators are reported
separately, not counted as gaps.**

| Category | Count | % |
|---|---|---|
| L1 in-scope, directly taught | 42/42 | **100%** |
| CTSO 1.0 (co-curricular via FBLA) | 0/20 tagged | reported separately |
| Out-of-level (L2/Complementary) | 26 | not in scope |
| **Remaining L1 gaps** | **0** | — |

History: 37 direct / 31 gaps (65%) → extractor fix + high-confidence tagging (77%
of non-CTSO) → day-level reconcile (the overview now reads the same day-level tags
as the crosswalk) → level-aware scoring → tagged the last two L1 indicators (5.2.1
at Unit 3 Day 1; 3.3.2 via a new hardware segment in Unit 1 Day 3) → **100% L1, 0 gaps.**

## Applied this pass (high-confidence, evidence-cited)

| Indicator | Unit · Days | Evidence |
|---|---|---|
| 2.2.4 Implement conditional controls | U6 D1,2,6 | Days 1–2 if/else + nested conditionals; rubric "Control Structures" |
| 2.4.3 Student-created components | U6 D5,6 | Day 5 helper-function decomposition; rubric "Modularity 3+ functions" |
| 3.1.1 Abstractions hide implementation | U1 D3,4,5 | Abstraction-as-hiding-complexity, car/smartphone everyday objects |
| 5.3.4 Ethics in technologies | U5 D1,2,4 | Whole-unit digital citizenship/ethics framing |
| 5.3.5 Laws/regulations on software | U5 D1 | Copyright law, software licenses, Creative Commons |
| 2.5.6 Software life cycle | U8 D1,2 | Requirements→design→code→test→deploy (Create Task) |
| 2.5.10 Test cases | U8 D7 | "Systematic testing: normal inputs, edge cases" |
| 6.1.1 Network scalability/reliability | U12 D1,2,3 | Routers, fault tolerance, addressing, topology, protocol stack |
| 6.2.5 Protect against unauthorized access | U12 D6 | "Authentication: passwords, 2FA, biometrics" |
| 5.1.5 Maximize benefit/minimize harm | U16 D1 | "Who benefits, who is harmed" case-study evaluation |
| 5.1.6 Innovations evolve culture | U16 D1 | "Computing and Culture"; innovations changing social norms |

## Remaining 20 gaps — by level (ACS I is an L1 course)

Only **4 of the 20 gaps include L1** — the rest are L2/Complementary and are not
expected in an L1 course, so they are not true gaps for ACS I.

**True L1 gaps — now 2 (down from 4):**
- 3.3.2 Illustrate how computing systems implement logic/input/output through hardware — *thin; partially in U1 abstraction layers, would need a small content add*
- 5.2.1 Collaboration tools across cultures and career fields — *genuine; pair programming does not satisfy "different cultures/career fields"*

Resolved this pass (taught but untagged → tagged):
- 3.2.2 OS roles → U1 Day 3 (OS manages hardware, provides commands to apps)
- 5.2.2 Team-productivity collaboration → U3 Days 1, 3 (pair programming + Collaboration Quality Rubric)

**L2 / out-of-scope for L1 (16):** 2.1.3, 2.1.5, 2.1.6, 2.2.3, 2.2.5, 2.4.4, 2.4.5,
2.5.7, 2.5.8, 2.5.9, 2.5.11, 3.2.3, 4.2.3, 6.1.2, 6.1.3, 6.2.6.

## Remaining 20 gaps — your decision

### Likely genuine scope gaps (outside ACS I L1 — recommend leaving as gaps)
- 2.1.3 Implement an AI/ML algorithm
- 2.2.3 Illustrate recursion flow · 2.2.5 Implement recursion *(recursion not taught in CS1)*
- 2.5.8 Multi-platform programs
- 2.5.9 Version control / IDEs / group software project
- 2.5.11 Modify an existing program to add functionality (L2)
- 3.2.2 OS roles · 3.2.3 Virtualization · 3.3.2 Hardware logic/input/output
- 5.2.1 Collaboration across cultures/career fields
- 6.1.3 Cloud vs. local deployment
- 6.2.6 Security scanning tools in the dev process (L2)

### Medium-confidence (plausibly coverable — your call, per unit)
| Indicator | Candidate unit | Note |
|---|---|---|
| 2.1.5 Develop classic algorithms in code | U2 / U9 | |
| 2.1.6 Evaluate algorithm efficiency/correctness/clarity | U9 | |
| 2.4.4 Analyze large problem, find generalizable patterns | U8 / U17 | |
| 2.4.5 Code reuse via libraries/APIs (L2) | U4 / U8 / U14 | p5.js, Chart.js |
| 2.5.7 Explain security issues in programs | U5 / U12 | |
| 4.2.3 Select data collection tools (L2) | U15 | data selection for Data Insight PT |
| 5.2.2 Collaboration for team productivity | U3 / U7 | pair programming |
| 6.1.2 Network functionality (bandwidth/load/delay) | U12 | |

## Notes
- **Unit 17 (Capstone)** is intentionally untagged ("synthesizes all standards,
  no discrete per-day standards"). Treated as integrative by design, not a gap.
- **CTSO 1.0 (20 indicators)** is credited as co-curricular via FBLA with no
  per-lesson trace. The auditor shows it as a separate category; consider whether
  a compliance reviewer will accept co-curricular coverage without lesson evidence.
