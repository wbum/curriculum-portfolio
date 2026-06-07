import os
import re
import json

reports_dir = os.path.dirname(os.path.abspath(__file__))
vault_path = os.path.dirname(reports_dir)  # Portfolio_Site is parent
vault_root = os.path.dirname(vault_path)    # TheVault is grandparent

# Load the compiled standards so we can map flat descriptions
standards_file = os.path.join(reports_dir, "dgd_cs_standards_grounded.json")
with open(standards_file, 'r', encoding='utf-8') as fh:
    content_standards = json.load(fh)

flat_standards_map = {}
for c_code, c_data in content_standards.items():
    for p_code, p_data in c_data["performance_standards"].items():
        for i_code, i_data in p_data["indicators"].items():
            flat_standards_map[i_code] = i_data["description"]

# ==========================================
# PARSE DGD II COURSE MAP (DGD_II UNITS)
# ==========================================
dgd2_path = os.path.join(vault_root, "03_Teaching/DGD_II")
course_data = {
    "units": [],
    "standards": {}
}

unit_dirs = []
for name in os.listdir(dgd2_path):
    dir_path = os.path.join(dgd2_path, name)
    if os.path.isdir(dir_path) and name.startswith("Unit_"):
        try:
            num = int(name.split("_")[1])
            unit_dirs.append((num, dir_path))
        except ValueError:
            continue

unit_dirs.sort(key=lambda x: x[0])

std_re = re.compile(r"DGD[\.\s]+(\d+\.\d+\.\d+)")

for unit_num, unit_dir in unit_dirs:
    unit_info = {
        "number": unit_num,
        "title": f"Unit {unit_num}",
        "days": [],
        "standards": []
    }
    
    lessons_file = os.path.join(unit_dir, f"Unit_{unit_num}_Lessons.md")
    if not os.path.exists(lessons_file):
        print(f"Warning: {lessons_file} not found")
        continue
        
    with open(lessons_file, 'r', encoding='utf-8') as fh:
        content = fh.read()
        
    # Extract Unit Title from first H1
    h1_match = re.search(r"^#\s+(Unit\s+\d+:\s*(.+?)\s*—\s*Lesson Plans|.+)$", content, re.MULTILINE)
    if h1_match:
        t = h1_match.group(1).strip()
        t_clean = re.sub(r"^Unit\s+\d+:\s*", "", t)
        t_clean = re.sub(r"\s*—\s*Lesson Plans", "", t_clean)
        unit_info["title"] = t_clean.strip()
        
    # Find all sessions (using H2 headings like "## DAY" or "## FRIDAY")
    sessions = re.split(r"^##\s+(?:DAY|FRIDAY)\s+", content, flags=re.MULTILINE)[1:]
    
    for idx, sess_raw in enumerate(sessions):
        sess_lines = sess_raw.splitlines()
        if not sess_lines:
            continue
            
        header_line = sess_lines[0].strip()
        m_title = re.match(r"^(\d+)\s*[:—\-]\s*(.+)$", header_line)
        sess_num = idx + 1
        sess_title = header_line
        if m_title:
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

# Filter standards map to only include standards we have descriptions for
course_data["standards"] = {code: flat_standards_map.get(code, "Digital Game Development Standard") for code in flat_standards_map}

out_json_course = os.path.join(reports_dir, "dgd2_course_map_grounded.json")
with open(out_json_course, 'w', encoding='utf-8') as fh:
    json.dump(course_data, fh, indent=2)

print(f"Course map data with canonical titles and merged standards written to {out_json_course}!")
print("Done DGD II compilation!")
