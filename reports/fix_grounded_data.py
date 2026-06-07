import os
import re
import json

vault_path = "/Users/willbumgardner/Desktop/TheVault"

# ==========================================
# 1. PARSE NV STANDARDS (WITH MULTI-LINE DESCRIPTIONS)
# ==========================================

txt_file = os.path.join(vault_path, "reports/nv_cs_standards.txt")
out_json_standards = os.path.join(vault_path, "reports/nv_cs_standards_grounded.json")

with open(txt_file, 'r', encoding='utf-8') as fh:
    lines = fh.readlines()

content_standards = {}
current_content = ""
current_perf = ""

i = 0
while i < len(lines):
    line = lines[i].strip()
    
    # Stop parsing if we reach complementary courses
    if i > 400 and ("Complementary Courses" in line or "State Complementary Skill Standards" in line):
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
                "Complementary Courses" in next_line or 
                "State Complementary Skill Standards" in next_line):
                break
                
            # Skip empty lines, page numbers, or form feeds
            if not next_line or next_line.isdigit() or next_line == "\x0c" or next_line.startswith("\x0c"):
                j += 1
                continue
                
            text_parts.append(next_line)
            
            # Check for level tag at the end (L1/L2/C) inside nested parentheses
            m_level = re.search(r"\((?:[^()]+|\([^()]*\))*\)\s*$", next_line)
            if m_level:
                level_str = m_level.group(0).strip("()")
                # Clean level string: e.g. "Level 1, (L1), Level 2, (L2), Complementary (C)"
                levels = []
                if "L1" in level_str or "Level 1" in level_str:
                    levels.append("L1")
                if "L2" in level_str or "Level 2" in level_str:
                    levels.append("L2")
                if "C" in level_str or "Complementary" in level_str:
                    levels.append("C")
                level = ", ".join(levels) if levels else level_str
                
                # Strip level block from the text part
                text_parts[-1] = next_line[:m_level.start()].strip()
                j += 1
                break
                
            j += 1
            
        # Join the text parts into a single line description
        description = " ".join(text_parts).strip()
        description = re.sub(r"\s+", " ", description)
        
        # Fallback if no level tag was found in lookahead
        if not level:
            m_level = re.search(r"\((?:[^()]+|\([^()]*\))*\)\s*$", description)
            if m_level:
                level_str = m_level.group(0).strip("()")
                levels = []
                if "L1" in level_str or "Level 1" in level_str:
                    levels.append("L1")
                if "L2" in level_str or "Level 2" in level_str:
                    levels.append("L2")
                if "C" in level_str or "Complementary" in level_str:
                    levels.append("C")
                level = ", ".join(levels) if levels else level_str
                description = description[:m_level.start()].strip()
            else:
                level = "L1"
                
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

print(f"1. Standards parsed: {len(content_standards)} Content Standards written to {out_json_standards}")


# ==========================================
# 2. EXTRACT CANONICAL COURSE MAP UNIT TITLES
# ==========================================

review_file = os.path.join(vault_path, "03_Teaching/ACS_I/ACS_I_Course_Review.md")
unit_titles = {}

with open(review_file, 'r', encoding='utf-8') as fh:
    review_content = fh.read()

for line in review_content.splitlines():
    if line.strip().startswith("|"):
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) >= 2:
            unit_str = cells[0]
            title_cell = cells[1]
            if unit_str.isdigit():
                unit_num = int(unit_str)
                # Clean title: e.g. [[Unit_1_Master_Overview\|Intro to CS...]] -> Intro to CS...
                title = title_cell.replace("\\|", "|")
                m_wiki = re.search(r"\[\[(?:[^|]+\|)?(.*?)\]\]", title)
                if m_wiki:
                    title = m_wiki.group(1)
                title = title.replace("[[", "").replace("]]", "").strip()
                unit_titles[unit_num] = title

print(f"2. Extracted {len(unit_titles)} canonical unit titles from course review.")


# ==========================================
# 3. MERGE AND UPDATE COURSE MAP JSON
# ==========================================

acs_path = os.path.join(vault_path, "03_Teaching/ACS_I")
course_data = {
    "units": [],
    "standards": {}
}

unit_dirs = []
unit_folder_re = re.compile(r"ACS1 Unit (\d+)")
for name in os.listdir(acs_path):
    dir_path = os.path.join(acs_path, name)
    if os.path.isdir(dir_path):
        m = unit_folder_re.match(name)
        if m:
            unit_dirs.append((int(m.group(1)), dir_path))

unit_dirs.sort(key=lambda x: x[0])

std_re = re.compile(r"(ADVCS\.\d+\.\d+\.\d+)")

# Flat standards descriptions mapping we compile
flat_standards_map = {}
for c_code, c_data in content_standards.items():
    for p_code, p_data in c_data["performance_standards"].items():
        for i_code, i_data in p_data["indicators"].items():
            flat_standards_map[i_code] = i_data["description"]

for unit_num, unit_dir in unit_dirs:
    unit_info = {
        "number": unit_num,
        "title": unit_titles.get(unit_num, f"Unit {unit_num}"),
        "days": [],
        "standards": []
    }
    
    day_files = []
    for f in os.listdir(unit_dir):
        if f.endswith("Lesson_Plan.md") and ("Day_" in f or "Day" in f):
            day_files.append(f)
            
    def get_day_num(filename):
        m = re.search(r"Day_(\d+)", filename)
        if m:
            return int(m.group(1))
        m2 = re.search(r"(\d+)", filename)
        return int(m2.group(1)) if m2 else 999
        
    day_files.sort(key=get_day_num)
    
    for df in day_files:
        df_path = os.path.join(unit_dir, df)
        day_num = get_day_num(df)
        
        with open(df_path, 'r', encoding='utf-8') as fh:
            day_content = fh.read()
            
        # Robust day title extraction (check H2 first, then H1)
        h2_match = re.search(r"^##\s+(.+)$", day_content, re.MULTILINE)
        h1_match = re.search(r"^#\s+(.+)$", day_content, re.MULTILINE)
        
        day_title = f"Day {day_num}"
        if h2_match:
            day_title = h2_match.group(1).strip()
        elif h1_match:
            day_title = h1_match.group(1).strip()
            
        # Clean day title
        day_title = re.sub(r"^(Unit\s*\d+,\s*Day\s*\d+:\s*|Unit\s*\d+\s*Day\s*\d+[:\s—\-]*|Day\s*\d+[:\s—\-]*|Lesson Plan\s*[:\s—\-]*|Practice PT\s*[:\s—\-]*)", "", day_title, flags=re.IGNORECASE)
        day_title = re.sub(r"\[\[.*?\|(.*?)\]\]", r"\1", day_title)
        day_title = re.sub(r"\[\[(.*?)\]\]", r"\1", day_title)
        day_title = day_title.replace("Lesson Plan", "").strip(" :—-•\u2014")
        
        day_stds = []
        all_matches = std_re.findall(day_content)
        for code in all_matches:
            if code not in day_stds:
                day_stds.append(code)
            if code not in unit_info["standards"]:
                unit_info["standards"].append(code)
                
        unit_info["days"].append({
            "day": day_num,
            "title": day_title,
            "standards": day_stds
        })
        
    course_data["units"].append(unit_info)

course_data["standards"] = {code: flat_standards_map.get(code, "Nevada Computer Science Standard") for code in flat_standards_map}

out_json_course = os.path.join(vault_path, "reports/acs1_course_map_grounded.json")
with open(out_json_course, 'w', encoding='utf-8') as fh:
    json.dump(course_data, fh, indent=2)

print(f"3. Course map data with canonical titles and merged standards written to {out_json_course}!")
print("Done fixing datasets!")
