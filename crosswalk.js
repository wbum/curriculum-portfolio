// CTE Computer Science Standards compliance auditor logic

// Global State
let activeCourse = 'acs_i'; // 'acs_i' or 'wdd_i' or 'dgd_i' or 'dgd_ii' or 'cet'
let standardsData = null;
let courseMapData = null;
let flatIndicators = {}; // normalizedCode -> indicatorObj
let stdToLessons = {}; // normalizedCode -> array of lesson references
let activeFilters = {
  level: 'all',
  coverage: 'all',
  search: ''
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
  const urlParams = new URLSearchParams(window.location.search);
  const courseParam = urlParams.get('course');
  if (courseParam === 'acs_i' || courseParam === 'wdd_i' || courseParam === 'dgd_i' || courseParam === 'dgd_ii' || courseParam === 'cet') {
    activeCourse = courseParam;
    const selectCourse = document.getElementById('select-course');
    if (selectCourse) selectCourse.value = courseParam;
    
    // Update active syllabus name in UI
    const activeSyllabusEl = document.getElementById('stat-active-syllabus');
    if (activeSyllabusEl) {
      activeSyllabusEl.textContent = activeCourse === 'acs_i' 
        ? 'Advanced CS I' 
        : activeCourse === 'wdd_i'
          ? 'Web Dev & Design I'
          : activeCourse === 'dgd_i'
            ? 'Digital Game Design I'
            : activeCourse === 'dgd_ii'
              ? 'Digital Game Design II (Bridge Year)'
              : 'Computer Education Tech';
    }

    // Hide or show FBLA option in coverage select
    const selectCoverage = document.getElementById('filter-coverage');
    if (selectCoverage) {
      const fblaOption = selectCoverage.querySelector('option[value="fbla"]');
      const coveredOption = selectCoverage.querySelector('option[value="covered"]');
      if (activeCourse === 'wdd_i' || activeCourse === 'cet') {
        if (fblaOption) fblaOption.style.display = 'none';
        if (coveredOption) coveredOption.textContent = 'All Covered';
        if (selectCoverage.value === 'fbla') selectCoverage.value = 'all';
      } else {
        if (fblaOption) fblaOption.style.display = 'block';
        if (coveredOption) coveredOption.textContent = 'All Covered (Direct + CTSO)';
      }
    }
  }
  loadData();
  setupEventListeners();
});

// Load Grounded Data
async function loadData() {
  try {
    const standardsFile = activeCourse === 'acs_i' 
      ? 'reports/nv_cs_standards_grounded.json' 
      : activeCourse === 'wdd_i'
        ? 'reports/wdd_cs_standards_grounded.json'
        : (activeCourse === 'dgd_i' || activeCourse === 'dgd_ii')
          ? 'reports/dgd_cs_standards_grounded.json'
          : 'reports/cet_cs_standards_grounded.json';
    const courseMapFile = activeCourse === 'acs_i' 
      ? 'reports/acs1_course_map_grounded.json' 
      : activeCourse === 'wdd_i'
        ? 'reports/wdd_course_map_grounded.json'
        : activeCourse === 'dgd_i'
          ? 'reports/dgd_course_map_grounded.json'
          : activeCourse === 'dgd_ii'
            ? 'reports/dgd2_course_map_grounded.json'
            : 'reports/cet_course_map_grounded.json';

    const [stdsRes, courseRes] = await Promise.all([
      fetch(standardsFile),
      fetch(courseMapFile)
    ]);

    if (!stdsRes.ok || !courseRes.ok) {
      throw new Error('Failed to load JSON data. Ensure the server is running and files exist in reports/.');
    }

    standardsData = await stdsRes.json();
    courseMapData = await courseRes.json();

    // Process and index datasets
    indexData();
    calculateStats();
    renderAuditor();

    // Auto-select standard from URL query param
    const urlParams = new URLSearchParams(window.location.search);
    const selectCode = urlParams.get('select');
    if (selectCode) {
      activeFilters.level = 'all';
      activeFilters.coverage = 'all';
      activeFilters.search = '';
      
      const selectLevelEl = document.getElementById('filter-level');
      const selectCoverageEl = document.getElementById('filter-coverage');
      const inputSearchEl = document.getElementById('search-query');
      if (selectLevelEl) selectLevelEl.value = 'all';
      if (selectCoverageEl) selectCoverageEl.value = 'all';
      if (inputSearchEl) inputSearchEl.value = '';
      
      renderAuditor();
      setTimeout(() => {
        selectStandard(selectCode);
      }, 150);
    } else {
      renderDefaultDetailsPanel();
    }
  } catch (error) {
    console.error('Error loading auditor data:', error);
    const container = document.getElementById('auditor-app');
    if (container) {
      container.innerHTML = `
        <div class="alert-panel warning">
          <div class="alert-title">Data Load Error</div>
          <p>Could not initialize the standards data: ${error.message}</p>
          <p>Make sure you are running a local web server (e.g. <code>python3 -m http.server</code>) from the workspace root.</p>
        </div>
      `;
    }
  }
}

// Normalize codes (e.g. ADVCS.2.1.2 -> 2.1.2)
function normalizeCode(code) {
  return code.replace('ADVCS.', '').replace('WDD ', '').replace('WEB ', '').replace('DGD.', '').replace('DGD ', '').replace('9-12.', '').trim();
}

// Process and index the JSON data for bidirectional mapping
function indexData() {
  flatIndicators = {};
  stdToLessons = {};

  // 1. Flatten standards catalog
  for (const cCode in standardsData) {
    // WDD I Rule: Standard 1.0 (CTSOs/FBLA) is explicitly excluded
    if (activeCourse === 'wdd_i' && cCode === '1.0') {
      continue;
    }

    const contentStd = standardsData[cCode];
    for (const pCode in contentStd.performance_standards) {
      const perfStd = contentStd.performance_standards[pCode];
      for (const iCode in perfStd.indicators) {
        const ind = perfStd.indicators[iCode];
        
        flatIndicators[iCode] = {
          code: iCode,
          parentContentCode: cCode,
          parentContentTitle: contentStd.title,
          parentPerfCode: pCode,
          parentPerfTitle: perfStd.title,
          description: ind.description,
          level: ind.level || 'L1'
        };
        stdToLessons[iCode] = [];
      }
    }
  }

  // 2. Map course lessons to standards
  courseMapData.units.forEach(unit => {
    unit.days.forEach(day => {
      if (day.standards && day.standards.length > 0) {
        day.standards.forEach(rawCode => {
          const normCode = normalizeCode(rawCode);
          if (stdToLessons[normCode]) {
            stdToLessons[normCode].push({
              unitNum: unit.number,
              unitTitle: unit.title,
              dayNum: day.day,
              dayTitle: day.title
            });
          }
        });
      }
    });
  });
}

// Calculate coverage stats
function calculateStats() {
  let total = 0;
  let directCovered = 0;
  let fblaCovered = 0;
  let gaps = 0;
  let outOfScope = 0; // uncovered but not expected at L1 (L2/Complementary, or excluded CTSO)

  // Each course is scored against indicators at ITS level. ACS I / WDD I / DGD I
  // are L1; DGD II is the L2 bridge year; CET is single-level (L1). An indicator
  // is in-scope when its level tag includes the course's level.
  const COURSE_LEVEL = { acs_i: 'L1', wdd_i: 'L1', dgd_i: 'L1', dgd_ii: 'L2', cet: 'L1' };
  const courseLevel = COURSE_LEVEL[activeCourse] || 'L1';

  for (const code in flatIndicators) {
    total++;
    const isCTSO = code.startsWith('1.');
    const inScope = (flatIndicators[code].level || 'L1').includes(courseLevel);
    if (activeCourse === 'wdd_i' && isCTSO) {
      outOfScope++; // WDD excludes CTSO Standard 1.0 by design
    } else if (stdToLessons[code] && stdToLessons[code].length > 0) {
      directCovered++;
    } else if ((activeCourse === 'acs_i' || activeCourse === 'dgd_i' || activeCourse === 'dgd_ii') && isCTSO) {
      fblaCovered++; // Treated as co-curricular via CTSO (FBLA/SkillsUSA)
    } else if (inScope) {
      gaps++; // uncovered AND in this course's level scope = a real gap
    } else {
      outOfScope++; // uncovered out-of-level (L2/Complementary) indicator — not expected
    }
  }

  // Denominator excludes out-of-scope indicators so a course isn't penalized for
  // out-of-level (L2/Complementary) indicators it isn't meant to teach.
  // inScopeTotal === directCovered + fblaCovered + gaps.
  const inScopeTotal = total - outOfScope;
  const directPercent = inScopeTotal > 0 ? Math.round((directCovered / inScopeTotal) * 100) : 0;
  const fblaPercent = inScopeTotal > 0 ? Math.round((fblaCovered / inScopeTotal) * 100) : 0;
  const totalPercent = inScopeTotal > 0 ? Math.round(((directCovered + fblaCovered) / inScopeTotal) * 100) : 0;

  // Update UI stats elements if they exist
  const pctCoveredEl = document.getElementById('stat-pct-covered');
  const totalStdsEl = document.getElementById('stat-total-stds');
  const directStdsEl = document.getElementById('stat-direct-stds');
  const fblaStdsEl = document.getElementById('stat-fbla-stds');
  const gapsStdsEl = document.getElementById('stat-gaps-stds');
  const oosStdsEl = document.getElementById('stat-oos-stds');
  const progressFillEl = document.getElementById('progress-bar-fill');
  const fblaRowEl = document.getElementById('stat-fbla-row');

  if (fblaRowEl) {
    fblaRowEl.style.display = (activeCourse === 'wdd_i' || activeCourse === 'cet') ? 'none' : 'block';
  }

  if (pctCoveredEl) pctCoveredEl.textContent = `${totalPercent}%`;
  if (totalStdsEl) totalStdsEl.textContent = inScopeTotal;
  if (directStdsEl) {
    directStdsEl.textContent = (activeCourse === 'wdd_i' || activeCourse === 'cet') 
      ? `${directCovered} indicators (${totalPercent}%)`
      : `${directCovered} indicators (${directPercent}%)`;
  }
  if (fblaStdsEl) fblaStdsEl.textContent = `${fblaCovered} indicators (${fblaPercent}%)`;
  if (gapsStdsEl) gapsStdsEl.textContent = `${gaps} indicators`;
  if (oosStdsEl) oosStdsEl.textContent = `${outOfScope} indicators`;
  if (progressFillEl) progressFillEl.style.width = `${totalPercent}%`;
}

// Set up UI Event Listeners
function setupEventListeners() {
  const selectCourse = document.getElementById('select-course');
  const selectLevel = document.getElementById('filter-level');
  const selectCoverage = document.getElementById('filter-coverage');
  const inputSearch = document.getElementById('search-query');
  const btnReset = document.getElementById('btn-reset-filters');
  const btnExport = document.getElementById('btn-export-audit');

  if (selectCourse) {
    selectCourse.addEventListener('change', (e) => {
      activeCourse = e.target.value;

      // Update active syllabus name in UI
      const activeSyllabusEl = document.getElementById('stat-active-syllabus');
      if (activeSyllabusEl) {
        activeSyllabusEl.textContent = activeCourse === 'acs_i' 
          ? 'Advanced CS I' 
          : activeCourse === 'wdd_i'
            ? 'Web Dev & Design I'
            : activeCourse === 'dgd_i'
              ? 'Digital Game Design I'
              : activeCourse === 'dgd_ii'
                ? 'Digital Game Design II (Bridge Year)'
                : 'Computer Education Tech';
      }

      // Hide or show FBLA option in coverage select
      if (selectCoverage) {
        const fblaOption = selectCoverage.querySelector('option[value="fbla"]');
        const coveredOption = selectCoverage.querySelector('option[value="covered"]');
        if (activeCourse === 'wdd_i' || activeCourse === 'cet') {
          if (fblaOption) fblaOption.style.display = 'none';
          if (coveredOption) coveredOption.textContent = 'All Covered';
          if (selectCoverage.value === 'fbla') selectCoverage.value = 'all';
        } else {
          if (fblaOption) fblaOption.style.display = 'block';
          if (coveredOption) coveredOption.textContent = 'All Covered (Direct + CTSO)';
        }
      }

      // Reset selections and filters
      activeFilters = { level: 'all', coverage: 'all', search: '' };
      if (selectLevel) selectLevel.value = 'all';
      if (selectCoverage) selectCoverage.value = 'all';
      if (inputSearch) inputSearch.value = '';

      clearSelections();
      loadData();
    });
  }

  if (selectLevel) {
    selectLevel.addEventListener('change', (e) => {
      activeFilters.level = e.target.value;
      renderAuditor();
    });
  }

  if (selectCoverage) {
    selectCoverage.addEventListener('change', (e) => {
      activeFilters.coverage = e.target.value;
      renderAuditor();
    });
  }

  if (inputSearch) {
    inputSearch.addEventListener('input', (e) => {
      activeFilters.search = e.target.value.toLowerCase();
      renderAuditor();
    });
  }

  if (btnReset) {
    btnReset.addEventListener('click', () => {
      if (selectLevel) selectLevel.value = 'all';
      if (selectCoverage) selectCoverage.value = 'all';
      if (inputSearch) inputSearch.value = '';
      activeFilters = { level: 'all', coverage: 'all', search: '' };
      renderAuditor();
      clearSelections();
      renderDefaultDetailsPanel();
    });
  }

  if (btnExport) {
    btnExport.addEventListener('click', () => {
      window.print();
    });
  }

  const btnExportMd = document.getElementById('btn-export-md');
  if (btnExportMd) {
    btnExportMd.addEventListener('click', downloadMarkdownReport);
  }
}

// Human-readable course name for the active course
function getCourseName(course) {
  switch (course) {
    case 'acs_i': return 'Advanced Computer Science I';
    case 'wdd_i': return 'Web Development & Design I';
    case 'dgd_i': return 'Digital Game Design I';
    case 'dgd_ii': return 'Digital Game Design II (Bridge Year)';
    case 'cet': return 'Computer Education Technology';
    default: return 'Course';
  }
}

// Classify an indicator's coverage, mirroring calculateStats() so the
// downloaded report matches the headline coverage percentage exactly.
// Returns: 'direct' | 'fbla' | 'gap' | 'scope' | 'excluded'
function classifyIndicator(code) {
  const ind = flatIndicators[code];
  const isCTSO = code.startsWith('1.');
  const inL1Scope = (ind.level || 'L1').includes('L1');

  if (activeCourse === 'wdd_i' && isCTSO) return 'excluded';
  if (stdToLessons[code] && stdToLessons[code].length > 0) return 'direct';
  if ((activeCourse === 'acs_i' || activeCourse === 'dgd_i' || activeCourse === 'dgd_ii') && isCTSO) return 'fbla';
  if (inL1Scope) return 'gap';
  return 'scope';
}

// Build a structured Markdown compliance report for the active course
function generateMarkdownReport() {
  const courseName = getCourseName(activeCourse);
  const showFbla = activeCourse === 'acs_i' || activeCourse === 'dgd_i' || activeCourse === 'dgd_ii';
  const today = new Date().toISOString().slice(0, 10);

  const tally = { direct: 0, fbla: 0, gap: 0, scope: 0, excluded: 0 };
  for (const code in flatIndicators) tally[classifyIndicator(code)]++;

  const total = Object.keys(flatIndicators).length;
  const coveredPct = total > 0 ? Math.round(((tally.direct + tally.fbla) / total) * 100) : 0;

  const lines = [];
  lines.push(`# Standards Compliance Audit — ${courseName}`);
  lines.push('');
  lines.push(`*Generated ${today} · Nevada CTE Computer Science Standards · Auditor: willbumgardner.com*`);
  lines.push('');

  // Summary
  lines.push('## Summary');
  lines.push('');
  lines.push(`| Metric | Value |`);
  lines.push(`| --- | --- |`);
  lines.push(`| Total indicators audited | ${total} |`);
  lines.push(`| Covered by direct instruction | ${tally.direct} |`);
  if (showFbla) lines.push(`| Co-curricular (CTSO/FBLA) | ${tally.fbla} |`);
  lines.push(`| Level 1 gaps (action required) | ${tally.gap} |`);
  lines.push(`| Out of scope (L2 / Complementary) | ${tally.scope} |`);
  if (activeCourse === 'wdd_i') lines.push(`| Excluded by design (CTSO 1.0) | ${tally.excluded} |`);
  lines.push(`| **Overall coverage** | **${coveredPct}%** |`);
  lines.push('');

  // Gap section
  lines.push('## Level 1 Compliance Gaps (Action Required)');
  lines.push('');
  const gapCodes = Object.keys(flatIndicators).filter(c => classifyIndicator(c) === 'gap');
  if (gapCodes.length === 0) {
    lines.push('None — every Level 1 indicator in scope is covered by direct instruction.');
  } else {
    gapCodes.forEach(code => {
      lines.push(`- **${code}** [${flatIndicators[code].level}] — ${flatIndicators[code].description}`);
    });
  }
  lines.push('');

  // Full coverage detail, grouped by content area / performance standard
  lines.push('## Coverage Detail');
  lines.push('');
  for (const cCode in standardsData) {
    if (activeCourse === 'wdd_i' && cCode === '1.0') continue;
    const contentStd = standardsData[cCode];
    let contentHeaderWritten = false;

    for (const pCode in contentStd.performance_standards) {
      const perfStd = contentStd.performance_standards[pCode];
      let perfHeaderWritten = false;

      for (const iCode in perfStd.indicators) {
        if (!flatIndicators[iCode]) continue;
        if (!contentHeaderWritten) {
          lines.push(`### Content Area ${cCode}: ${contentStd.title}`);
          lines.push('');
          contentHeaderWritten = true;
        }
        if (!perfHeaderWritten) {
          lines.push(`#### Standard ${pCode}: ${perfStd.title}`);
          lines.push('');
          perfHeaderWritten = true;
        }

        const ind = flatIndicators[iCode];
        const kind = classifyIndicator(iCode);
        lines.push(`- **${iCode}** [${ind.level}] — ${ind.description}`);

        if (kind === 'direct') {
          stdToLessons[iCode].forEach(ref => {
            lines.push(`  - ✓ Covered: Unit ${ref.unitNum} (${ref.unitTitle}) — Day ${ref.dayNum}: ${ref.dayTitle}`);
          });
        } else if (kind === 'fbla') {
          lines.push('  - ✓ Co-curricular via CTSO (FBLA) — chapter activities, competitions, leadership conferences');
        } else if (kind === 'gap') {
          lines.push('  - ✗ GAP — no direct instruction mapped');
        } else if (kind === 'excluded') {
          lines.push('  - — Excluded by design (CTSO Standard 1.0)');
        } else {
          lines.push(`  - — Beyond Level 1 scope (${ind.level}); no action required`);
        }
      }
      if (perfHeaderWritten) lines.push('');
    }
  }

  return lines.join('\n');
}

// Generate and trigger download of the Markdown report
function downloadMarkdownReport() {
  if (!standardsData || !courseMapData) return;
  const md = generateMarkdownReport();
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const today = new Date().toISOString().slice(0, 10);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${activeCourse}-standards-audit-${today}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Render columns
function renderAuditor() {
  renderStandardsTree();
  renderLessonsList();
}

// Render Standards Tree Column
function renderStandardsTree() {
  const treeContainer = document.getElementById('standards-tree');
  if (!treeContainer) return;

  treeContainer.innerHTML = '';
  let visibleIndicatorsCount = 0;

  // We loop through content standards to preserve structure
  for (const cCode in standardsData) {
    const contentStd = standardsData[cCode];
    let contentHeaderAdded = false;

    for (const pCode in contentStd.performance_standards) {
      const perfStd = contentStd.performance_standards[pCode];
      let perfHeaderAdded = false;

      for (const iCode in perfStd.indicators) {
        const ind = flatIndicators[iCode];
        
        // Apply Filters
        const matchesLevel = activeFilters.level === 'all' || 
          (activeFilters.level === 'L1' && ind.level.includes('L1')) ||
          (activeFilters.level === 'L2' && ind.level.includes('L2')) ||
          (activeFilters.level === 'C' && ind.level.includes('C'));

        const isFbla = iCode.startsWith('1.');
        const isCovered = (stdToLessons[iCode] && stdToLessons[iCode].length > 0) || isFbla;

        const matchesCoverage = activeFilters.coverage === 'all' ||
          (activeFilters.coverage === 'covered' && isCovered) ||
          (activeFilters.coverage === 'direct' && stdToLessons[iCode] && stdToLessons[iCode].length > 0) ||
          (activeFilters.coverage === 'fbla' && isFbla) ||
          (activeFilters.coverage === 'gap' && !isCovered);

        const searchLower = activeFilters.search;
        const matchesSearch = !searchLower || 
          iCode.includes(searchLower) ||
          ind.description.toLowerCase().includes(searchLower) ||
          ind.parentContentTitle.toLowerCase().includes(searchLower) ||
          ind.parentPerfTitle.toLowerCase().includes(searchLower);

        if (matchesLevel && matchesCoverage && matchesSearch) {
          visibleIndicatorsCount++;

          // Lazy render headers to avoid empty sections
          if (!contentHeaderAdded) {
            const cHeader = document.createElement('div');
            cHeader.className = 'content-standard-header';
            cHeader.innerHTML = `<h3>Content Area ${cCode}: ${contentStd.title}</h3>`;
            treeContainer.appendChild(cHeader);
            contentHeaderAdded = true;
          }

          if (!perfHeaderAdded) {
            const pHeader = document.createElement('div');
            pHeader.className = 'perf-standard-header';
            pHeader.innerHTML = `<h4>Standard ${pCode}: ${perfStd.title}</h4>`;
            treeContainer.appendChild(pHeader);
            perfHeaderAdded = true;
          }

          // Render Indicator item
          const item = document.createElement('div');
          item.className = 'std-indicator-item';
          item.dataset.code = iCode;

          const isFblaCode = iCode.startsWith('1.');
          const lessonsMapping = stdToLessons[iCode] || [];
          const lessonsCount = lessonsMapping.length;

          const inL1Scope = (ind.level || 'L1').includes('L1');
          let statusHtml = '';
          if (activeCourse === 'wdd_i' && isFblaCode) {
            statusHtml = `<span class="std-coverage-status status-scope">CTSO 1.0 — excluded by design</span>`;
          } else if (lessonsCount > 0) {
            statusHtml = `<span class="std-coverage-status status-covered">✓ Covered (${lessonsCount} Class${lessonsCount > 1 ? 'es' : ''})</span>`;
          } else if (activeCourse !== 'wdd_i' && isFblaCode) {
            statusHtml = `<span class="std-coverage-status status-covered">✓ Co-curricular (CTSO)</span>`;
          } else if (inL1Scope) {
            statusHtml = `<span class="std-coverage-status status-gap">✗ Gap Identified</span>`;
          } else {
            statusHtml = `<span class="std-coverage-status status-scope">Beyond L1 scope (${ind.level})</span>`;
          }

          item.innerHTML = `
            <div class="std-indicator-header">
              <span class="std-code">${iCode}</span>
              <span class="std-level-tag">${ind.level}</span>
            </div>
            <div class="std-desc">${ind.description}</div>
            <div>${statusHtml}</div>
          `;

          item.addEventListener('click', () => selectStandard(iCode));
          treeContainer.appendChild(item);
        }
      }
    }
  }

  // Update visible indicator count
  const countEl = document.getElementById('standards-count');
  if (countEl) countEl.textContent = visibleIndicatorsCount;
  
  if (visibleIndicatorsCount === 0) {
    treeContainer.innerHTML = '<div class="p-4 text-center text-secondary">No standards match the active filters.</div>';
  }
}

// Render Lessons List Column
function renderLessonsList() {
  const listContainer = document.getElementById('lessons-list');
  if (!listContainer) return;

  listContainer.innerHTML = '';
  let visibleLessonsCount = 0;

  courseMapData.units.forEach(unit => {
    let unitHeaderAdded = false;

    unit.days.forEach(day => {
      // Find matches if search is active (either in unit title, day title, or standard codes)
      const searchLower = activeFilters.search;
      const matchesSearch = !searchLower ||
        unit.title.toLowerCase().includes(searchLower) ||
        day.title.toLowerCase().includes(searchLower) ||
        day.standards.some(code => normalizeCode(code).toLowerCase().includes(searchLower));

      if (matchesSearch) {
        visibleLessonsCount++;

        if (!unitHeaderAdded) {
          const uHeader = document.createElement('div');
          uHeader.className = 'unit-lesson-header';
          uHeader.innerHTML = `<h4>Unit ${unit.number}: ${unit.title}</h4>`;
          listContainer.appendChild(uHeader);
          unitHeaderAdded = true;
        }

        const item = document.createElement('div');
        item.className = 'lesson-item';
        item.dataset.unit = unit.number;
        item.dataset.day = day.day;

        const stdPills = day.standards.map(rawCode => {
          const norm = normalizeCode(rawCode);
          return `<span class="lesson-std-pill" data-code="${norm}">${norm}</span>`;
        }).join(' ');

        item.innerHTML = `
          <div class="lesson-meta">Unit ${unit.number} · Day ${day.day}</div>
          <div class="lesson-title">${day.title}</div>
          <div class="lesson-stds-list">${stdPills || '<span class="text-secondary" style="font-size:0.75rem;">No direct standards mapped</span>'}</div>
        `;

        item.addEventListener('click', (e) => {
          // If clicked a standard pill inside, select that standard instead
          if (e.target.classList.contains('lesson-std-pill')) {
            e.stopPropagation();
            selectStandard(e.target.dataset.code);
          } else {
            selectLesson(unit.number, day.day);
          }
        });

        listContainer.appendChild(item);
      }
    });
  });

  const countEl = document.getElementById('lessons-count');
  if (countEl) countEl.textContent = visibleLessonsCount;

  if (visibleLessonsCount === 0) {
    listContainer.innerHTML = '<div class="p-4 text-center text-secondary">No lessons match the active filters.</div>';
  }
}

// Select a Standard: Highlight it and its mapped lessons
function selectStandard(code) {
  clearSelections();

  const stdEl = document.querySelector(`.std-indicator-item[data-code="${code}"]`);
  if (stdEl) {
    stdEl.classList.add('selected');
    stdEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // Highlight all mapped lessons
  const mapped = stdToLessons[code] || [];
  
  // Update Details Panel
  renderDetailsPanelForStandard(code, mapped);

  if (mapped.length > 0) {
    mapped.forEach(ref => {
      const lessonEl = document.querySelector(`.lesson-item[data-unit="${ref.unitNum}"][data-day="${ref.dayNum}"]`);
      if (lessonEl) {
        lessonEl.classList.add('highlight-mapped');
      }
    });

    // Scroll first mapped lesson into view
    const firstRef = mapped[0];
    const firstEl = document.querySelector(`.lesson-item[data-unit="${firstRef.unitNum}"][data-day="${firstRef.dayNum}"]`);
    if (firstEl) {
      firstEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }
}

// Select a Lesson: Highlight it and its mapped standards
function selectLesson(unitNum, dayNum) {
  clearSelections();

  const lessonEl = document.querySelector(`.lesson-item[data-unit="${unitNum}"][data-day="${dayNum}"]`);
  if (lessonEl) {
    lessonEl.classList.add('selected');
    lessonEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // Find standards mapped to this lesson
  let lessonData = null;
  const unit = courseMapData.units.find(u => u.number === parseInt(unitNum));
  if (unit) {
    lessonData = unit.days.find(d => d.day === parseInt(dayNum));
  }

  // Update Details Panel
  renderDetailsPanelForLesson(unitNum, dayNum, lessonData);

  if (lessonData && lessonData.standards && lessonData.standards.length > 0) {
    lessonData.standards.forEach(rawCode => {
      const norm = normalizeCode(rawCode);
      const stdEl = document.querySelector(`.std-indicator-item[data-code="${norm}"]`);
      if (stdEl) {
        stdEl.classList.add('highlight-mapped');
      }
    });

    // Scroll first mapped standard into view
    const firstNorm = normalizeCode(lessonData.standards[0]);
    const firstStdEl = document.querySelector(`.std-indicator-item[data-code="${firstNorm}"]`);
    if (firstStdEl) {
      firstStdEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }
}

// Clear all selected/highlight states
function clearSelections() {
  document.querySelectorAll('.std-indicator-item').forEach(el => el.classList.remove('selected', 'highlight-mapped'));
  document.querySelectorAll('.lesson-item').forEach(el => el.classList.remove('selected', 'highlight-mapped'));
}

// Render Standard details in the details panel
function renderDetailsPanelForStandard(code, mapped) {
  const panel = document.getElementById('details-display-panel');
  if (!panel) return;

  const ind = flatIndicators[code];
  if (!ind) return;

  const isFbla = code.startsWith('1.');
  const inL1Scope = (ind.level || 'L1').includes('L1');
  let coverageSection = '';

  if (isFbla && activeCourse === 'wdd_i') {
    coverageSection = `
      <div class="alert-panel" style="margin-top: 15px;">
        <div class="alert-title">Excluded by Design (CTSO 1.0)</div>
        <p>Career and Technical Student Organization (CTSO) Standard 1.0 is excluded from this course by design and is not counted as a gap.</p>
      </div>
    `;
  } else if (mapped.length > 0) {
    const listItems = mapped.map(ref => `
      <li>
        <a href="curriculum.html#unit-${ref.unitNum}" target="_blank">Unit ${ref.unitNum}: ${ref.unitTitle}</a>
        &ndash; Day ${ref.dayNum}: ${ref.dayTitle}
      </li>
    `).join('');
    coverageSection = `
      <div class="details-section">
        <h5>Mapped Lessons (${mapped.length})</h5>
        <ul class="mapped-lessons-list">${listItems}</ul>
      </div>
    `;
  } else if (isFbla) {
    coverageSection = `
      <div class="alert-panel success" style="margin-top: 15px;">
        <div class="alert-title">Co-curricular Compliance Pathway</div>
        <p>This Career and Technical Student Organization (CTSO) standard is integrated co-curricularly via <strong>CTSO Activities</strong>, chapter business meetings, leadership conferences, and project-based competitions. This bypasses standalone unit lessons to ensure authentic career simulation.</p>
      </div>
    `;
  } else if (inL1Scope) {
    coverageSection = `
      <div class="alert-panel warning" style="margin-top: 15px;">
        <div class="alert-title">Compliance Gap Identified</div>
        <p>This Level 1 performance indicator is not yet covered by direct instruction. Recommended action: add a supplementary instructional activity or map it to an existing lesson.</p>
      </div>
    `;
  } else {
    coverageSection = `
      <div class="alert-panel" style="margin-top: 15px;">
        <div class="alert-title">Beyond L1 Scope (${ind.level})</div>
        <p>This indicator is Level 2 / Complementary and is not expected in this Level 1 course, so it is not counted as a gap.</p>
      </div>
    `;
  }

  panel.innerHTML = `
    <div class="card">
      <div class="card-label">Standards Detail View</div>
      <h3 class="font-serif" style="margin-bottom: 5px;">${code}</h3>
      <div class="std-level-tag" style="display:inline-block; margin-bottom: 15px;">Level: ${ind.level}</div>
      
      <p style="font-size: 1.1rem; line-height: 1.5; margin-bottom: 20px; font-weight: 500;">
        ${ind.description}
      </p>
      
      <div style="border-top: 1px solid var(--border-color); padding-top: 15px; margin-top: 15px;">
        <div style="font-size:0.8rem; text-transform:uppercase; color:var(--text-secondary); margin-bottom:5px;">Content Area</div>
        <strong>${ind.parentContentCode} &ndash; ${ind.parentContentTitle}</strong>
      </div>
      
      <div style="border-top: 1px solid var(--border-color); padding-top: 15px; margin-top: 15px; margin-bottom: 15px;">
        <div style="font-size:0.8rem; text-transform:uppercase; color:var(--text-secondary); margin-bottom:5px;">Performance Standard</div>
        <strong>${ind.parentPerfCode} &ndash; ${ind.parentPerfTitle}</strong>
      </div>

      ${coverageSection}
    </div>
  `;
}

// Render Lesson details in the details panel
function renderDetailsPanelForLesson(unitNum, dayNum, lessonData) {
  const panel = document.getElementById('details-display-panel');
  if (!panel) return;

  if (!lessonData) {
    panel.innerHTML = `
      <div class="card text-center text-secondary">
        Select a standard indicator or course lesson to inspect compliance links.
      </div>
    `;
    return;
  }

  let standardsSection = '';
  if (lessonData.standards && lessonData.standards.length > 0) {
    const listItems = lessonData.standards.map(rawCode => {
      const norm = normalizeCode(rawCode);
      const ind = flatIndicators[norm];
      const desc = ind ? ind.description : 'Nevada Computer Science Standard';
      return `
        <li style="margin-bottom: 12px; cursor:pointer;" onclick="selectStandard('${norm}')">
          <strong class="color-accent" style="color:var(--color-accent); border-bottom:1px dashed var(--color-accent);">${norm}</strong>: ${desc}
        </li>
      `;
    }).join('');
    standardsSection = `
      <div class="details-section">
        <h5>Covered Standards (${lessonData.standards.length})</h5>
        <ul class="mapped-standards-list" style="list-style: none;">${listItems}</ul>
      </div>
    `;
  } else {
    standardsSection = `
      <div class="alert-panel" style="margin-top: 15px;">
        <div class="alert-title">Syllabus Context</div>
        <p>This class plan covers foundational coding practice, reflection, or assessments that support general CS literacy without mapping to a specific discrete compliance indicator.</p>
      </div>
    `;
  }

  panel.innerHTML = `
    <div class="card">
      <div class="card-label">Syllabus Lesson View</div>
      <h3 class="font-serif" style="margin-bottom: 5px;">Day ${dayNum}</h3>
      <div style="font-size: 0.95rem; font-weight: 700; color: var(--text-secondary); margin-bottom: 15px;">
        Unit ${unitNum}: ${courseMapData.units.find(u => u.number === parseInt(unitNum)).title}
      </div>
      
      <p style="font-size: 1.15rem; font-weight: 600; line-height: 1.4; margin-bottom: 20px;">
        ${lessonData.title}
      </p>

      <div style="border-top: 1px solid var(--border-color); padding-top: 15px; margin-top: 15px; margin-bottom: 15px;">
        ${standardsSection}
      </div>
      
      <div class="text-right" style="margin-top: 20px;">
        <a href="curriculum.html#unit-${unitNum}" class="btn" target="_blank">Open Unit Scope &amp; Sequence &rarr;</a>
      </div>
    </div>
  `;
}

// Render Default Details Panel showing Executive Gap Analysis
function renderDefaultDetailsPanel() {
  const panel = document.getElementById('details-display-panel');
  if (!panel) return;

  let l1Gaps = [];
  let l2Gaps = [];

  for (const code in flatIndicators) {
    const ind = flatIndicators[code];
    const isFbla = code.startsWith('1.');
    const isCovered = (stdToLessons[code] && stdToLessons[code].length > 0) || isFbla;

    if (!isCovered) {
      if ((ind.level || 'L1').includes('L1')) {
        l1Gaps.push({ code, desc: ind.description });
      } else {
        l2Gaps.push({ code, desc: ind.description });
      }
    }
  }

  const courseName = activeCourse === 'acs_i' 
    ? 'Advanced Computer Science I' 
    : activeCourse === 'wdd_i'
      ? 'Web Development & Design I'
      : activeCourse === 'dgd_i'
        ? 'Digital Game Design I'
        : activeCourse === 'dgd_ii'
          ? 'Digital Game Design II (Bridge Year)'
          : 'Computer Education Technology';
  const totalCount = Object.keys(flatIndicators).length;
  const totalGaps = l1Gaps.length + l2Gaps.length;

  const l1List = l1Gaps.map(g => `
    <li style="margin-bottom: 12px; font-size: 0.95rem; cursor: pointer; list-style-type: square; margin-left: 15px;" onclick="selectStandard('${g.code}')">
      <strong class="color-accent" style="color:var(--color-accent); border-bottom:1px dashed var(--color-accent);">${g.code}</strong>: ${g.desc}
    </li>
  `).join('');

  const bridgeAlert = activeCourse === 'dgd_ii' ? `
    <div class="alert-panel" style="margin-bottom: 20px; border-left-color: var(--color-accent); padding: var(--spacing-md);">
      <div class="alert-title" style="font-size: 0.85rem; font-weight: 700; color: var(--color-accent); margin-bottom: 8px;">
        Curriculum Implementation Note (Bridge Year)
      </div>
      <p style="font-size: 0.9rem; margin-bottom: 0; color: var(--text-primary); line-height: 1.4;">
        This Digital Game Design II syllabus represents a <strong>one-year bridge course</strong> designed specifically to satisfy missing Level 2 standards from the prior year-long CodeHS course sequence.
      </p>
    </div>
  ` : '';

  panel.innerHTML = `
    <div class="card" style="padding: var(--spacing-lg);">
      <div class="card-label">Syllabus Compliance Report</div>
      <h3 class="font-serif" style="margin-bottom: 10px;">Executive Gap Analysis Summary</h3>
      <p style="font-size: 0.95rem; color: var(--text-secondary); margin-bottom: 20px; line-height: 1.5;">
        ${courseName} has been audited against all ${totalCount} performance indicators.
        <strong>${l1Gaps.length} Level 1 gap${l1Gaps.length === 1 ? '' : 's'}</strong> require action;
        ${l2Gaps.length} further indicators are Level 2 / Complementary and outside this course's scope.
      </p>

      ${bridgeAlert}

      ${l1Gaps.length === 0 ? `
      <div class="alert-panel success" style="margin-bottom: 20px; border-left-width: 4px; padding: var(--spacing-md);">
        <div class="alert-title" style="font-size: 0.85rem; font-weight: 700; color: var(--color-success); margin-bottom: 8px;">
          Level 1 Coverage Complete &mdash; No Action Required
        </div>
        <p style="font-size: 0.9rem; margin-bottom: 0; color: var(--text-primary); line-height: 1.4;">
          Every Level 1 performance indicator in scope is covered by direct instruction.
        </p>
      </div>` : `
      <div class="alert-panel warning" style="margin-bottom: 20px; border-left-width: 4px; padding: var(--spacing-md);">
        <div class="alert-title" style="font-size: 0.85rem; font-weight: 700; color: var(--color-warning); margin-bottom: 8px;">
          Level 1 Course Scope Gaps (${l1Gaps.length}) &mdash; Action Required
        </div>
        <p style="font-size: 0.9rem; margin-bottom: 12px; color: var(--text-primary); line-height: 1.4;">
          These indicators fall within the Level 1 course scope but are currently missing direct instruction:
        </p>
        <ul style="padding-left: 0; margin-bottom: 0;">
          ${l1List}
        </ul>
      </div>`}

      <div class="alert-panel" style="margin-bottom: 0; border-left-color: var(--text-secondary); padding: var(--spacing-md);">
        <div class="alert-title" style="font-size: 0.85rem; font-weight: 700; color: var(--text-secondary); margin-bottom: 8px;">
          Level 2 / Complementary Gaps (${l2Gaps.length}) &mdash; Out of Scope
        </div>
        <p style="font-size: 0.9rem; margin-bottom: 0; color: var(--text-secondary); line-height: 1.4;">
          These ${l2Gaps.length} indicators are reserved for Level 2 (advanced pathways) or Complementary curricula (e.g., specialized scripting or server management). <strong>No compliance action is required</strong> for the Level 1 syllabus scope.
        </p>
      </div>
    </div>
  `;
}
