# Grounded Build Plan: Professional Curriculum Portfolio & Standards Crosswalk Tool

This updated document outlines the architecture, design system, data model, and phase-by-phase implementation plan for a combined **Curriculum Portfolio Site** and **Interactive Standards Crosswalk Tool**. This plan is built directly from the actual data extracted from your vault.

---

## 1. Project Overview & Career Positioning

To target **district-level CS leadership, state CTE offices, and remote EdTech curriculum roles**, your work must look and feel like it belongs in curriculum leadership:
* **The Buyer Persona:** State and district education directors, CTE administrators, and hiring committees. They value structure, compliance, accessibility, and pedagogical rigor.
* **The Portfolio Site:** Displays your custom-built CS courses (ACS I, WDD I, DGD I, DGD II, CET) as polished, peer-reviewed products with clear standards coverage and AI literacy scaffolds.
* **The Crosswalk Tool:** Integrated as a live, working artifact. Instead of a developer-focused tech demo, it behaves like an administrative tool for curriculum audit compliance.

---

## 2. Design System & Aesthetics (Swiss / Light Editorial)

We are abandoning dark-mode glassmorphism (which reads as a tech-startup or developer dashboard) in favor of a **Swiss/Light Editorial** design system. This provides a clean, authoritative, and academic aesthetic.

### Visual Architecture
* **Background Canvas:** Warm off-white / book-paper hue: HSL `(35, 20%, 98%)`
* **Card & Content Background:** Soft bone / light grey: HSL `(210, 10%, 94%)`
* **Text Primary:** Deep Charcoal (softer than pure black): HSL `(210, 25%, 12%)`
* **Text Secondary:** Slate Gray: HSL `(210, 10%, 45%)`
* **Accent Colors:** 
  * Primary Accent: Deep Academic Blue: HSL `(215, 60%, 25%)`
  * Secondary Accent: Sage Green (for compliance/checkmarks): HSL `(145, 30%, 42%)`
* **Borders & Grids:** Thin, high-contrast structural grid lines (`1px solid HSL(210, 10%, 80%)`) instead of box shadows or blurry backdrops.
* **Typography:** 
  * Headings: Elegant, high-readability Serif (e.g., Lora or Playfair Display) for an editorial, textbook-like quality.
  * Body & Interface: Clean, geometric Sans-Serif (e.g., Inter) for sharp tables and interactive controls.

---

## 3. Data Integration: Genuinely Grounded

The Crosswalk Tool will run on the actual JSON databases extracted from your vault:

### A. Mapped Course Data
Derived directly from your 17-unit Advanced CS I lesson plans:
* **Source Path:** [acs1_course_map_grounded.json](file:///Users/willbumgardner/Desktop/TheVault/reports/acs1_course_map_grounded.json) (compiled from `03_Teaching/ACS_I/`)
* **Format:** Lists all 17 units, their day-by-day topics (e.g., Karel removal, p5.js, Steganography, Chart.js), and the exact standard codes matched to each lesson.

### B. Nevada CTE CS Standards
Derived directly from the official Nevada Department of Education standards document:
* **Source Path:** [nv_cs_standards_grounded.json](file:///Users/willbumgardner/Desktop/TheVault/reports/nv_cs_standards_grounded.json) (compiled from `Advanced_Computer_Sci_Comp_STDS_c66f3a8093.pdf`)
* **Format:** Structured catalog of Content Standards 1.0–7.0, Performance Standards, and all 88 specific performance indicators with their official L1/L2 course level tags.

---

## 4. Interactive Crosswalk Tool (Compliance Auditor)

The tool will render as a professional, grid-based **CTE Standards Compliance Auditor**.

```
+-------------------------------------------------------------------------+
|  NEVADA CTE COMPUTER SCIENCE STANDARDS COMPLIANCE AUDITOR               |
+-------------------------------------------------------------------------+
| Active Course: [ Advanced CS I (LCSD) v ]    Filter Standards: [ L1 only v ] |
|                                                                         |
| Standards Coverage:  =======================[ 76% Covered ]             |
|                                                                         |
| Content Standard 2.0: Algorithms & Programming                          |
| [x] 2.1.2 Describe how AI drives systems...... Covered in: Unit 1 Days 2, 6 |
| [x] 2.2.1 Justify control structure selection.. Covered in: Unit 11 Day 1 |
| [ ] 2.3.1 Demonstrate LinkedLists/ArrayLists... [GAP IDENTIFIED]        |
+-------------------------------------------------------------------------+
| [ View Gap Analysis Report ]               [ Export Audit Documentation ] |
+-------------------------------------------------------------------------+
```

### Core Workflows
1. **Interactive Auditor:** Users browse the NV standards. Clicking a standard highlights the exact unit(s) and day(s) in your course where it is taught, showing the lesson objective.
2. **Real Gap Identification:** Gaps (like Standard 1.0 CTSO co-curricular requirements or L2 indicators) are flagged with explanatory design choices (e.g., *"Carried via co-curricular FBLA Friday Threads, not direct instruction"*).
3. **Data-Driven Export:** Generates printable, clean audit reports matching NDE compliance formats.

---

## 5. Phase-by-Phase Build Steps

### **Phase 1: Visual Framing & Navigation**
* [ ] Create core files: `index.html` (Landing/Resume), `curriculum.html` (Unit reviews), `crosswalk.html` (Auditor tool), `style.css`.
* [ ] Establish the Swiss-Editorial style tokens in `style.css` (warm page canvas, grid borders, serif headers, custom print styles).
* [ ] Build the responsive navigation bar and landing page layout.

### **Phase 2: Integrating Vault Datasets**
* [ ] Combine [acs1_course_map_grounded.json](file:///Users/willbumgardner/Desktop/TheVault/reports/acs1_course_map_grounded.json) and [nv_cs_standards_grounded.json](file:///Users/willbumgardner/Desktop/TheVault/reports/nv_cs_standards_grounded.json) into a unified local client-side data controller (`crosswalk_data.js`).
* [ ] Implement the layout structure for the standards tree and course mapping interface.

### **Phase 3: Interactive Auditor Development**
* [ ] Build filter controls (e.g., showing only L1 standards, or searching by keyword like "AI").
* [ ] Write the interactive selection highlights (hovering a standard highlights its mapped lesson; clicking a lesson reveals covered standards).
* [ ] Program the real-time coverage percentage dial and dynamic gap analyzer panel.

### **Phase 4: Compliance Exporter & Polish**
* [ ] Add a clean print-stylesheet so the crosswalk output format compiles into a professional printed PDF/paper report.
* [ ] Write the markdown export module.
* [ ] Add SEO meta tags and descriptive titles.
