# Attribution — 2026 CSTA PK–12 Computer Science Standards

`csta2026_standards.txt` and `csta2026_standards_grounded.json` in this directory
contain the text of the **2026 CSTA PK–12 Computer Science Standards**, extracted
from the official PDF and restructured for machine use.

> 2026 CSTA PK–12 Computer Science Standards
> © 2026 Computer Science Teachers Association (CSTA)
> Licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)
> <https://csteachers.org/pk12standards/>

CSTA publishes these standards under CC BY-NC-SA 4.0, which permits downloading,
sharing, and adapting the materials in whole or in part, for non-commercial use,
with attribution and share-alike. This repository is a non-commercial personal
curriculum portfolio.

**What was changed:** the standards were extracted from the PDF with
`pdftotext -layout` and parsed by `parse_csta2026.py` into a three-level JSON
catalog (concept → subconcept → standard). Standard statements, boundary
statements, practices, and dispositions are reproduced verbatim; the concept and
subconcept names are transcribed from the naming-convention tables in the source
document. No standard text was reworded.

Derived analysis in `csta2026-coverage.md` is original work and describes how
four locally authored courses align to these standards. CSTA has not reviewed or
endorsed that analysis, and it is not a CSTA Standards Alignment Review.
