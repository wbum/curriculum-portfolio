import os
import re
import json

from dgd_lessons import parse_units
from validate_data import write_json_validated

# Use relative path since the script runs inside Portfolio_Site/reports/
reports_dir = os.path.dirname(os.path.abspath(__file__))
vault_path = os.path.dirname(reports_dir)  # Portfolio_Site is parent
vault_root = os.path.dirname(vault_path)    # TheVault is grandparent

# ==========================================
# 1. PARSE DGD STANDARDS
# ==========================================
txt_file = os.path.join(reports_dir, "dgd_standards.txt")
out_json_standards = os.path.join(reports_dir, "dgd_cs_standards_grounded.json")

print(f"Reading standards from: {txt_file}")
with open(txt_file, 'r', encoding='utf-8') as fh:
    lines = fh.readlines()

content_standards = {}
current_content = ""
current_perf = ""

def normalize_level(paren_text: str) -> str:
    # Replace common OCR/conversion errors (e.g. 12 -> L1, 22 -> L2)
    paren_text = paren_text.replace("12", "L1").replace("22", "L2")
    found = [t for t in ("L1", "L2", "C") if re.search(rf"\b{re.escape(t)}\b", paren_text)]
    if not found:
        return "L1"
    return ", ".join(found)

# Page-break furniture that the PDF->text conversion interleaves into the
# standards body. These lines must never be treated as indicator descriptions
# and must be stripped before level detection (they push the trailing "(L2)"
# level marker away from end-of-string and defeat detection).
FOOTER_RE = re.compile(
    r"\s*(?:"
    r"Nevada CTE Standards(?:\s+Revised:\s*\d{1,2}/\d{1,2}/\d{2,4})?"
    r"|Digital Game Development Standards"
    r"|Revised:\s*\d{1,2}/\d{1,2}/\d{2,4}"
    r")\s*",
    re.IGNORECASE,
)

# A description is "complete" only when it ends with a level marker like
# "(L1)", "(L2)", or "(L1, L2)". Used to detect wrapped continuation lines.
LEVEL_END_RE = re.compile(r"\([^()]*\b(?:L1|L2|C|12|22)\b[^()]*\)\s*$")

def is_page_furniture(s: str) -> bool:
    if not s or s.isdigit() or s == "\x0c" or s.startswith("\x0c"):
        return True
    return bool(FOOTER_RE.search(s))

def strip_footer(buf: str) -> str:
    return FOOTER_RE.sub(" ", buf).strip()

def split_desc_level(buf: str):
    buf = strip_footer(buf)
    # Pick the LAST parenthetical that actually names a level, wherever it sits.
    # This survives embedded parens like "(LOD)" earlier in the description.
    for m in reversed(list(re.finditer(r"\(([^()]*)\)", buf))):
        if re.search(r"\b(?:L1|L2|C|12|22)\b", m.group(1)):
            level = normalize_level(m.group(1))
            desc = (buf[:m.start()] + buf[m.end():]).strip()
            return desc.strip(), level
    return buf.strip(), "L1"

buffered_codes = []
buffered_descriptions = []

i = 0
while i < len(lines):
    line = lines[i].strip()
    
    # Stop parsing if we reach complementary courses or end of main standards
    if i > 800 and ("Complementary Course" in line or "State Complementary Skill" in line):
        print(f"Reached Complementary Courses section at line {i+1}. Stopping standards parser.")
        break
        
    # Content Standard
    m_content = re.search(r"CONTENT STANDARD (\d+\.\d+):\s*(.+)", line, re.IGNORECASE)
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
    m_perf = re.search(r"Performance Standard (\d+\.\d+):\s*(.+)", line, re.IGNORECASE)
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

    # Detect standalone indicator codes (stacked layout like 2.1.1 on its own line)
    m_code_only = re.match(r"^(\d+\.\d+\.\d+)$", line)
    if m_code_only:
        buffered_codes.append(m_code_only.group(1))
        i += 1
        continue

    # If we have buffered codes, we look for non-empty, non-header lines to match them as descriptions
    if buffered_codes and line and not is_page_furniture(line):
        # Ensure it's not a standard header
        if not (re.search(r"CONTENT STANDARD", line, re.IGNORECASE) or
                re.search(r"Performance Standard", line, re.IGNORECASE) or
                "Complementary Course" in line):
            # A line that arrives while the previous description still lacks a
            # trailing level marker is a wrapped continuation, not a new entry.
            if buffered_descriptions and not LEVEL_END_RE.search(buffered_descriptions[-1]):
                buffered_descriptions[-1] = (buffered_descriptions[-1] + " " + line).strip()
            else:
                buffered_descriptions.append(line)

            # Pair up only once every code has a complete (level-terminated) description
            if (len(buffered_descriptions) == len(buffered_codes)
                    and LEVEL_END_RE.search(buffered_descriptions[-1])):
                for c_code, desc in zip(buffered_codes, buffered_descriptions):
                    desc, level = split_desc_level(desc)
                    desc = desc.strip(" :-*")
                    
                    content_num = c_code.split(".")[0] + ".0"
                    perf_num = ".".join(c_code.split(".")[:2])
                    
                    if content_num in content_standards:
                        if perf_num in content_standards[content_num]["performance_standards"]:
                            content_standards[content_num]["performance_standards"][perf_num]["indicators"][c_code] = {
                                "description": desc,
                                "level": level
                            }
                # Clear buffers
                buffered_codes = []
                buffered_descriptions = []
            i += 1
            continue

    # Standard inline performance indicator (code and description on same line)
    m_ind = re.match(r"^(\d+\.\d+\.\d+)\s+(.+)$", line)
    if m_ind:
        code = m_ind.group(1)
        first_line_text = m_ind.group(2).strip()
        
        text_parts = [first_line_text]
        j = i + 1
        
        # Lookahead to collect wrapped lines
        while j < len(lines):
            next_line = lines[j].strip()
            
            if (re.search(r"CONTENT STANDARD", next_line, re.IGNORECASE) or 
                re.search(r"Performance Standard", next_line, re.IGNORECASE) or 
                re.match(r"^\d+\.\d+\.\d+", next_line) or
                "Complementary Course" in next_line):
                break
                
            if is_page_furniture(next_line):
                j += 1
                continue

            text_parts.append(next_line)
            j += 1
            
        description = " ".join(text_parts).strip()
        description = re.sub(r"\s+", " ", description)
        description, level = split_desc_level(description)
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

write_json_validated(out_json_standards, content_standards, "catalog")

print(f"1. DGD Standards parsed: {len(content_standards)} Content Standards written to {out_json_standards}")


# ==========================================
# 2. PARSE DGD COURSE MAP (DGD_I UNITS)
# ==========================================
dgd_path = os.path.join(vault_root, "03_Teaching/DGD_I")
course_data = {
    "units": [],
    "standards": {}
}

# Flat standards descriptions mapping we compile
flat_standards_map = {}
for c_code, c_data in content_standards.items():
    for p_code, p_data in c_data["performance_standards"].items():
        for i_code, i_data in p_data["indicators"].items():
            flat_standards_map[i_code] = i_data["description"]

# Meeting parsing lives in dgd_lessons so it can be tested without running this
# whole pipeline. The unit files use "## WEEK n · SESSION m (DAY, 40 min) — Title"
# since the block-to-daily re-pace; see that module for why day numbers come from
# document order rather than the SESSION/FRIDAY labels.
course_data["units"] = parse_units(dgd_path)
for unit_info in course_data["units"]:
    print(f"Unit {unit_info['number']}: {len(unit_info['days'])} meetings, "
          f"{len(unit_info['standards'])} standards — {unit_info['title']}")

# Filter standards map to only include standards we have descriptions for
course_data["standards"] = {code: flat_standards_map.get(code, "Digital Game Development Standard") for code in flat_standards_map}

out_json_course = os.path.join(reports_dir, "dgd_course_map_grounded.json")
write_json_validated(out_json_course, course_data, "course_map")

print(f"2. Course map data with canonical titles and merged standards written to {out_json_course}!")
print("Done DGD compilation!")
