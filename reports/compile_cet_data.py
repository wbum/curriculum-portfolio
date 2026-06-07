import os
import re
import json

reports_dir = os.path.dirname(os.path.abspath(__file__))
vault_path = os.path.dirname(reports_dir)  # Portfolio_Site is parent
vault_root = os.path.dirname(vault_path)    # TheVault is grandparent

# ==========================================
# 1. PARSE CET STANDARDS
# ==========================================
txt_file = os.path.join(reports_dir, "cet_standards_temp.txt")
out_json_standards = os.path.join(reports_dir, "cet_cs_standards_grounded.json")

print(f"Reading CET standards from: {txt_file}")
with open(txt_file, 'r', encoding='utf-8') as fh:
    lines = fh.readlines()

# Hierarchy mappings
perf_standard_titles = {
    "AP": "Algorithms and Programming",
    "CS": "Computing Systems",
    "DA": "Data and Analysis",
    "IC": "Impacts of Computing",
    "NI": "Networks and the Internet",
    "EL": "Empowered Learner",
    "DC": "Digital Citizen",
    "KC": "Knowledge Constructor",
    "ID": "Innovative Designer",
    "CT": "Computational Thinker",
    "CC": "Creative Communicator",
    "GC": "Global Collaborator"
}

content_standard_titles = {
    "CS": "Computer Science and Computational Thinking Concepts",
    "IT": "Integrated Technology Concepts"
}

content_standards = {
    "CS": {
        "title": content_standard_titles["CS"],
        "performance_standards": {}
    },
    "IT": {
        "title": content_standard_titles["IT"],
        "performance_standards": {}
    }
}

def normalize_code(code: str) -> str:
    # Remove whitespace and '9-12.' prefix
    return code.replace("9-12.", "").replace(" ", "").strip()

i = 0
while i < len(lines):
    line = lines[i].strip()
    
    # Match standard code pattern: 9-12. <prefix>.<subprefix>.<num>
    # Note: allowing optional space after the dot in 9-12.
    m_ind = re.match(r"^9-12\.\s*([A-Z]+)\.([A-Z\d]+)\.(\d+)\s*[-–]\s*(.+)$", line)
    if m_ind:
        prefix = m_ind.group(1)
        subprefix = m_ind.group(2)
        num = m_ind.group(3)
        code = f"{prefix}.{subprefix}.{num}"
        first_line_text = m_ind.group(4).strip()
        
        text_parts = [first_line_text]
        j = i + 1
        
        # Lookahead to collect wrapped lines
        while j < len(lines):
            next_line = lines[j].strip()
            
            if (re.match(r"^9-12\.\s*[A-Z]+\.[A-Z\d]+\.\d+", next_line) or
                "Concepts" in next_line or "Standards" in next_line or
                next_line == "\x0c" or next_line.startswith("\x0c")):
                break
                
            if not next_line or next_line.isdigit():
                j += 1
                continue
                
            text_parts.append(next_line)
            j += 1
            
        description = " ".join(text_parts).strip()
        description = re.sub(r"\s+", " ", description)
        
        # Determine category (CS vs IT)
        cat = "CS" if prefix in ["AP", "CS", "DA", "IC", "NI"] else "IT"
        
        # Ensure performance standard exists
        if prefix not in content_standards[cat]["performance_standards"]:
            content_standards[cat]["performance_standards"][prefix] = {
                "title": perf_standard_titles.get(prefix, f"{prefix} Standard"),
                "indicators": {}
            }
            
        content_standards[cat]["performance_standards"][prefix]["indicators"][code] = {
            "description": description,
            "level": "L1" # All CET graduation standards are treated as L1 for this course
        }
        
        i = j
        continue
    i += 1

with open(out_json_standards, 'w', encoding='utf-8') as fh:
    json.dump(content_standards, fh, indent=2)

print(f"1. CET Standards parsed: {len(content_standards)} Content Standards written to {out_json_standards}")


# ==========================================
# 2. PARSE CET COURSE MAP (DAYS 1-90)
# ==========================================
cet_path = os.path.join(vault_root, "03_Teaching/CET")
course_data = {
    "units": [],
    "standards": {}
}

# Define the 5 Blocks as units in our syllabus map
blocks_info = [
    {"num": 1, "name": "Block_0_Launch", "title": "Launch: Course Framing & Goals", "days_range": range(1, 3)},
    {"num": 2, "name": "Block_A_Digital_Citizenship", "title": "Digital Citizenship & Cyber Hygiene", "days_range": range(3, 16)},
    {"num": 3, "name": "Block_B_VEX_AIM", "title": "VEX AIM Robotics", "days_range": range(16, 59)},
    {"num": 4, "name": "Block_C_Data_Connected_World", "title": "Data & the Connected World", "days_range": range(59, 74)},
    {"num": 5, "name": "Block_D_Build_Communicate", "title": "Build & Communicate", "days_range": range(74, 91)}
]

std_re = re.compile(r"9-12\.\s*[A-Z]+\.[A-Z\d]+\.\d+")

# Flat standards descriptions mapping
flat_standards_map = {}
for c_code, c_data in content_standards.items():
    for p_code, p_data in c_data["performance_standards"].items():
        for i_code, i_data in p_data["indicators"].items():
            flat_standards_map[i_code] = i_data["description"]

# VEX unit-specific day mapping inside Block B (relative days)
vex_units = [
    {"num": 1, "file": "Unit_1_Overview.md", "start_day": 16, "end_day": 19},
    {"num": 2, "file": "Unit_2_Overview.md", "start_day": 20, "end_day": 24},
    {"num": 3, "file": "Unit_3_Overview.md", "start_day": 25, "end_day": 29},
    {"num": 4, "file": "Unit_4_Overview.md", "start_day": 30, "end_day": 34},
    {"num": 5, "file": "Unit_5_Overview.md", "start_day": 35, "end_day": 39},
    {"num": 6, "file": "Unit_6_Overview.md", "start_day": 40, "end_day": 44},
    {"num": 7, "file": "Unit_7_Overview.md", "start_day": 45, "end_day": 47},
    {"num": 8, "file": "Unit_8_Overview.md", "start_day": 48, "end_day": 52},
    {"num": 9, "file": "Unit_9_Capstone_Overview.md", "start_day": 53, "end_day": 58}
]

for block in blocks_info:
    unit_info = {
        "number": block["num"],
        "title": block["title"],
        "days": [],
        "standards": []
    }
    
    block_dir = os.path.join(cet_path, block["name"])
    
    if block["name"] != "Block_B_VEX_AIM":
        # Parse individual day lesson plan files
        for day in block["days_range"]:
            filename = f"Day_{day}_Lesson_Plan.md"
            filepath = os.path.join(block_dir, filename)
            
            if not os.path.exists(filepath):
                print(f"Warning: Lesson file {filepath} not found")
                continue
                
            with open(filepath, 'r', encoding='utf-8') as fh:
                content = fh.read()
                
            # Extract title from H1
            h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = f"Day {day} Lesson"
            if h1_match:
                h1_text = h1_match.group(1).strip()
                if ":" in h1_text:
                    title = h1_text.split(":", 1)[1].strip()
                else:
                    title = h1_text
            
            # Extract standards from the Lesson Overview table
            day_stds = []
            for line in content.splitlines():
                if re.search(r"\|\s*Standards\s*\|", line, re.IGNORECASE):
                    matches = std_re.findall(line)
                    for m in matches:
                        norm = normalize_code(m)
                        if norm not in day_stds:
                            day_stds.append(norm)
                        if norm not in unit_info["standards"]:
                            unit_info["standards"].append(norm)
            
            unit_info["days"].append({
                "day": day,
                "title": title,
                "standards": day_stds
            })
    else:
        # Block B VEX AIM Robotics: parse unit overviews
        for vex_u in vex_units:
            filepath = os.path.join(block_dir, vex_u["file"])
            if not os.path.exists(filepath):
                print(f"Warning: VEX unit overview {filepath} not found")
                continue
                
            with open(filepath, 'r', encoding='utf-8') as fh:
                content = fh.read()
                
            # Find all standards in the unit overview file
            unit_stds = []
            matches = std_re.findall(content)
            for m in matches:
                norm = normalize_code(m)
                if norm not in unit_stds:
                    unit_stds.append(norm)
                if norm not in unit_info["standards"]:
                    unit_info["standards"].append(norm)
                    
            # Parse day table rows
            day_rows = []
            in_table = False
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("|"):
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 4 and parts[1].isdigit():
                        day_rows.append((int(parts[1]), parts[-2]))
                        
            # Map VEX unit relative days to absolute course days
            for rel_day, focus in day_rows:
                abs_day = vex_u["start_day"] + rel_day - 1
                # Check bounds safety
                if abs_day <= vex_u["end_day"]:
                    unit_info["days"].append({
                        "day": abs_day,
                        "title": f"U{vex_u['num']}: {focus}",
                        "standards": unit_stds
                    })
                    
    course_data["units"].append(unit_info)

# Add standards descriptions mapping
course_data["standards"] = {code: flat_standards_map.get(code, "Computer Education Technology Standard") for code in flat_standards_map}

out_json_course = os.path.join(reports_dir, "cet_course_map_grounded.json")
with open(out_json_course, 'w', encoding='utf-8') as fh:
    json.dump(course_data, fh, indent=2)

print(f"2. Course map data with canonical titles and merged standards written to {out_json_course}!")
print("Done CET compilation!")
