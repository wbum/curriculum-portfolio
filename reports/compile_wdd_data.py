import os
import re
import json

vault_path = "/Users/willbumgardner/Desktop/TheVault"

# ==========================================
# 1. PARSE WDD STANDARDS
# ==========================================
txt_file = os.path.join(vault_path, "reports/wdd_standards.txt")
out_json_standards = os.path.join(vault_path, "reports/wdd_cs_standards_grounded.json")

with open(txt_file, 'r', encoding='utf-8') as fh:
    lines = fh.readlines()

content_standards = {}
current_content = ""
current_perf = ""

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
                
            # Skip empty lines, page numbers, or form feeds
            if not next_line or next_line.isdigit() or next_line == "\x0c" or next_line.startswith("\x0c"):
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

with open(out_json_standards, 'w', encoding='utf-8') as fh:
    json.dump(content_standards, fh, indent=2)

print(f"1. WDD Standards parsed: {len(content_standards)} Content Standards written to {out_json_standards}")


# ==========================================
# 2. PARSE WDD COURSE MAP (WDD_I UNITS)
# ==========================================
wdd_path = os.path.join(vault_path, "03_Teaching/WDD_I")
course_data = {
    "units": [],
    "standards": {}
}

unit_dirs = []
for name in os.listdir(wdd_path):
    dir_path = os.path.join(wdd_path, name)
    if os.path.isdir(dir_path) and name.startswith("Unit_"):
        try:
            num = int(name.split("_")[1])
            unit_dirs.append((num, dir_path))
        except ValueError:
            continue

unit_dirs.sort(key=lambda x: x[0])

std_re = re.compile(r"(?:WDD|WEB)\s+(\d+\.\d+\.\d+)")

# Flat standards descriptions mapping we compile
flat_standards_map = {}
for c_code, c_data in content_standards.items():
    for p_code, p_data in c_data["performance_standards"].items():
        for i_code, i_data in p_data["indicators"].items():
            flat_standards_map[i_code] = i_data["description"]

for unit_num, unit_dir in unit_dirs:
    unit_info = {
        "number": unit_num,
        "title": f"Unit {unit_num}",
        "days": [],
        "standards": []
    }
    
    lessons_file = os.path.join(unit_dir, "Redesign_Lessons.md")
    if not os.path.exists(lessons_file):
        print(f"Warning: Redesign_Lessons.md not found in {unit_dir}")
        continue
        
    with open(lessons_file, 'r', encoding='utf-8') as fh:
        content = fh.read()
        
    # Extract Unit Title from first H1
    h1_match = re.search(r"^#\s+(Unit\s+\d+:\s*(.+?)\s*—\s*Lesson Plans|.+)$", content, re.MULTILINE)
    if h1_match:
        t = h1_match.group(1).strip()
        # Clean title
        t_clean = re.sub(r"^Unit\s+\d+:\s*", "", t)
        t_clean = re.sub(r"\s*—\s*Lesson Plans", "", t_clean)
        unit_info["title"] = t_clean.strip()
        
    # Find all sessions (using H2 headings)
    sessions = re.split(r"^##\s+SESSION\s+", content, flags=re.MULTILINE)[1:]
    
    for idx, sess_raw in enumerate(sessions):
        sess_lines = sess_raw.splitlines()
        if not sess_lines:
            continue
            
        header_line = sess_lines[0].strip()
        # Header format: "1 — Title" or "1: Title"
        m_title = re.match(r"^(\d+)\s*[:—\-]\s*(.+)$", header_line)
        sess_num = idx + 1
        sess_title = header_line
        if m_title:
            sess_num = int(m_title.group(1))
            sess_title = m_title.group(2).strip()
            
        # Search for Standards metadata line immediately following
        sess_stds = []
        metadata_block = "\n".join(sess_lines[1:4])
        std_matches = std_re.findall(metadata_block)
        for code in std_matches:
            if code not in sess_stds:
                sess_stds.append(code)
            if code not in unit_info["standards"]:
                unit_info["standards"].append(code)
                
        unit_info["days"].append({
            "day": sess_num,
            "title": sess_title,
            "standards": sess_stds
        })
        
    course_data["units"].append(unit_info)

course_data["standards"] = {code: flat_standards_map.get(code, "Web Design and Development Standard") for code in flat_standards_map}

out_json_course = os.path.join(vault_path, "reports/wdd_course_map_grounded.json")
with open(out_json_course, 'w', encoding='utf-8') as fh:
    json.dump(course_data, fh, indent=2)

print(f"2. Course map data with canonical titles and merged standards written to {out_json_course}!")
print("Done WDD compilation!")
