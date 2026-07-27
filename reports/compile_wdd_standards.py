"""Parse the Nevada Web Design & Development standards into a grounded catalog.

Input is `wdd_standards.txt`, a text dump of the official standards PDF. Output is
`wdd_cs_standards_grounded.json`, which the site reads and which
`regen_wdd_course_map.py` reads to decide which codes are real.

This script used to also build the course map, but that half was superseded:
`regen_wdd_course_map.py` replaced it because the original extractor missed
bare-code shorthand and expanded no ranges, inventing phantom gaps. Only the
catalog half lives here now, so the worse extractor cannot be run by accident.

Standard 1.0 (CTSOs/FBLA) stays in the catalog because the PDF prescribes it; it
is excluded from gap reporting downstream, not here.
"""
import os
import re
import json

from validate_data import write_json_validated

reports_dir = os.path.dirname(os.path.abspath(__file__))

# ==========================================
# 1. PARSE WDD STANDARDS
# ==========================================
txt_file = os.path.join(reports_dir, "wdd_standards.txt")
out_json_standards = os.path.join(reports_dir, "wdd_cs_standards_grounded.json")

with open(txt_file, 'r', encoding='utf-8') as fh:
    lines = fh.readlines()

content_standards = {}
current_content = ""
current_perf = ""

# Page-break furniture the PDF->text conversion interleaves into the standards
# body. It must never land in a description: it pushes the trailing "(L2)" level
# marker away from end-of-string and defeats level detection, silently
# downgrading every affected indicator to L1. Same failure as in
# compile_dgd_data.py, same shape of fix.
FOOTER_RE = re.compile(
    r"^\s*(?:"
    r"(?:\d+|[ivxlc]+)?\s*Nevada CTE Standards"
    r"|Web Design and Development Standards"
    r"|Revised:\s*\d{1,2}/\d{1,2}/\d{2,4}"
    r"|\d{4}"
    r")",
    re.IGNORECASE,
)


def is_page_furniture(line: str) -> bool:
    """True for a line that is page header/footer, not standards text."""
    if not line or line.isdigit() or line.startswith("\x0c"):
        return True
    return bool(FOOTER_RE.match(line)) and not re.match(r"^\d+\.\d+", line)


def normalize_level(paren_text: str) -> str:
    found = [t for t in ("L1", "L2", "C") if re.search(rf"\b{re.escape(t)}\b", paren_text)]
    return ", ".join(found)

def split_desc_level(buf: str):
    buf = re.sub(r"\s*Revised:\s*\d{1,2}/\d{1,2}/\d{2,4}\s*$", "", buf)
    m = re.search(r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*$", buf)
    if not m:
        return buf.strip(), "L1"
    level = normalize_level(m.group(1))
    if not level:  # trailing parens were part of the description, not a level tag
        return buf.strip(), "L1"
    return buf[:m.start()].strip(), level

i = 0
while i < len(lines):
    line = lines[i].strip()
    
    # Stop parsing if we reach complementary courses
    if i > 400 and ("Complementary Course" in line or "State Complementary Skill" in line):
        print(f"Reached Complementary Courses section at line {i+1}. Stopping standards parser.")
        break
        
    # Content Standard
    m_content = re.search(r"CONTENT STANDARD (\d+\.\d+):\s*(.+)", line)
    if m_content:
        num = m_content.group(1)
        name = m_content.group(2).strip()
        current_content = num
        content_standards[num] = {
            "title": name,
            "performance_standards": {}
        }
        i += 1
        continue
        
    # Performance Standard
    m_perf = re.search(r"Performance Standard (\d+\.\d+):\s*(.+)", line)
    if m_perf:
        num = m_perf.group(1)
        name = m_perf.group(2).strip()
        current_perf = num
        content_num = num.split(".")[0] + ".0"
        if content_num in content_standards:
            content_standards[content_num]["performance_standards"][num] = {
                "title": name,
                "indicators": {}
            }
        i += 1
        continue
        
    # Performance Indicator Start
    m_ind = re.match(r"^(\d+\.\d+\.\d+)\s+(.+)$", line)
    if m_ind:
        code = m_ind.group(1)
        first_line_text = m_ind.group(2).strip()
        
        text_parts = [first_line_text]
        j = i + 1
        level = None
        
        # Lookahead to collect wrapped lines
        while j < len(lines):
            next_line = lines[j].strip()
            
            # Stop if we hit a new header or indicator
            if (re.search(r"CONTENT STANDARD", next_line) or 
                re.search(r"Performance Standard", next_line) or 
                re.match(r"^\d+\.\d+\.\d+", next_line) or
                "Complementary Course" in next_line or 
                "State Complementary Skill" in next_line):
                break
                
            # Skip empty lines, page numbers, form feeds, and footer furniture
            if is_page_furniture(next_line):
                j += 1
                continue
                
            text_parts.append(next_line)
            j += 1
            
        # Join the text parts into a single line description
        description = " ".join(text_parts).strip()
        description = re.sub(r"\s+", " ", description)
        
        # Split description and level tag using our backtrack-safe helper
        description, level = split_desc_level(description)
                
        # Clean trailing parenthesis or tags in description
        description = description.strip(" :-*")
        
        content_num = code.split(".")[0] + ".0"
        perf_num = ".".join(code.split(".")[:2])
        
        if content_num in content_standards:
            if perf_num in content_standards[content_num]["performance_standards"]:
                content_standards[content_num]["performance_standards"][perf_num]["indicators"][code] = {
                    "description": description,
                    "level": level
                }
        
        i = j
        continue
        
    i += 1

write_json_validated(out_json_standards, content_standards, "catalog", indent=1)

print(f"1. WDD Standards parsed: {len(content_standards)} Content Standards written to {out_json_standards}")
