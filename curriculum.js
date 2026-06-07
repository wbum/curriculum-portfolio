// Curriculum Roadmap Browser Logic

let activeCourse = 'acs_i'; // 'acs_i' or 'wdd_i'
let courseData = null;
let standardsData = null;
let flatStandards = {};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  const urlParams = new URLSearchParams(window.location.search);
  const courseParam = urlParams.get('course');
  if (courseParam === 'acs_i' || courseParam === 'wdd_i' || courseParam === 'dgd_i' || courseParam === 'dgd_ii' || courseParam === 'cet') {
    activeCourse = courseParam;
    const selectCourse = document.getElementById('select-course');
    if (selectCourse) selectCourse.value = courseParam;
    
    // Update heading immediately
    const titleEl = document.getElementById('curriculum-title');
    if (titleEl) {
      titleEl.textContent = activeCourse === 'acs_i'
        ? 'Advanced Computer Science I'
        : activeCourse === 'wdd_i'
          ? 'Web Development & Design I'
          : activeCourse === 'dgd_i'
            ? 'Digital Game Design I'
            : activeCourse === 'dgd_ii'
              ? 'Digital Game Design II (Bridge Year)'
              : 'Computer Education Technology';
    }
  }
  loadSyllabusData();
  setupCourseSelector();
});

// Load Datasets
async function loadSyllabusData() {
  try {
    const courseMapFile = activeCourse === 'acs_i' 
      ? 'reports/acs1_course_map_grounded.json' 
      : activeCourse === 'wdd_i'
        ? 'reports/wdd_course_map_grounded.json'
        : activeCourse === 'dgd_i'
          ? 'reports/dgd_course_map_grounded.json'
          : activeCourse === 'dgd_ii'
            ? 'reports/dgd2_course_map_grounded.json'
            : 'reports/cet_course_map_grounded.json';
    const standardsFile = activeCourse === 'acs_i' 
      ? 'reports/nv_cs_standards_grounded.json' 
      : activeCourse === 'wdd_i'
        ? 'reports/wdd_cs_standards_grounded.json'
        : activeCourse === 'dgd_i'
          ? 'reports/dgd_cs_standards_grounded.json'
          : activeCourse === 'dgd_ii'
            ? 'reports/dgd_cs_standards_grounded.json'
            : 'reports/cet_cs_standards_grounded.json';

    const [courseRes, stdsRes] = await Promise.all([
      fetch(courseMapFile),
      fetch(standardsFile)
    ]);

    if (!courseRes.ok || !stdsRes.ok) {
      throw new Error('Failed to load JSON datasets.');
    }

    courseData = await courseRes.json();
    standardsData = await stdsRes.json();

    // Compile flat standards index for tooltips
    compileFlatStandards();
    
    // Render the page
    renderCurriculum();
    setupSearch();
  } catch (error) {
    console.error('Error loading curriculum data:', error);
    const container = document.getElementById('curriculum-accordion-container');
    if (container) {
      container.innerHTML = `
        <div class="alert-panel warning">
          <div class="alert-title">Curriculum Load Error</div>
          <p>Could not initialize syllabus data: ${error.message}</p>
          <p>Make sure you are running a local web server (e.g. <code>python3 -m http.server</code>) from the workspace root.</p>
        </div>
      `;
    }
  }
}

// Flatten standards tree for easy key-value lookup
function compileFlatStandards() {
  flatStandards = {};
  for (const cCode in standardsData) {
    const contentStd = standardsData[cCode];
    for (const pCode in contentStd.performance_standards) {
      const perfStd = contentStd.performance_standards[pCode];
      for (const iCode in perfStd.indicators) {
        flatStandards[iCode] = perfStd.indicators[iCode].description;
      }
    }
  }
}

// Render units accordion
function renderCurriculum() {
  const container = document.getElementById('curriculum-accordion-container');
  if (!container) return;

  container.innerHTML = '';
  let totalDays = 0;

  if (activeCourse === 'dgd_ii') {
    const alert = document.createElement('div');
    alert.className = 'alert-panel';
    alert.style.marginBottom = '20px';
    alert.innerHTML = `
      <div class="alert-title">Curriculum Implementation Note</div>
      <p style="font-size: 0.95rem; margin-bottom: 0;">
        This syllabus is configured as a <strong>one-year bridge course</strong> designed specifically to satisfy missing Level 2 standards from the prior year-long CodeHS course sequence.
      </p>
    `;
    container.appendChild(alert);
  }

  courseData.units.forEach(unit => {
    totalDays += unit.days.length;

    // Create mutually exclusive details element (using name="curriculum-units")
    const details = document.createElement('details');
    details.className = 'unit-block';
    details.name = 'curriculum-units';
    details.id = `unit-${unit.number}`;

    // Summary header
    const summary = document.createElement('summary');
    summary.innerHTML = `
      <span class="unit-summary-title">
        <span class="unit-badge">Unit ${unit.number}</span>
        ${unit.title}
      </span>
      <span class="unit-summary-meta">${unit.days.length} Day${unit.days.length > 1 ? 's' : ''} Mapped</span>
    `;

    // Inner details panel
    const detailsPanel = document.createElement('div');
    detailsPanel.className = 'unit-details';

    // Build day cards grid
    const dayGrid = document.createElement('div');
    dayGrid.className = 'day-grid';

    unit.days.forEach(day => {
      const dayCard = document.createElement('div');
      dayCard.className = 'day-card';
      dayCard.dataset.dayNum = day.day;
      dayCard.dataset.searchText = `${unit.title} ${day.title} ${day.standards.join(' ')}`.toLowerCase();

      // Render standard pills
      const stdPills = day.standards.map(rawCode => {
        const normCode = rawCode.replace('ADVCS.', '').replace('WDD ', '').replace('WEB ', '').replace('DGD.', '').replace('DGD ', '').replace('9-12.', '').trim();
        const desc = flatStandards[normCode] || 'Nevada CTE Standard';
        return `
          <a href="crosswalk.html?select=${normCode}" 
             class="lesson-std-pill" 
             title="${normCode}: ${desc}"
             target="_blank">${normCode}</a>
        `;
      }).join(' ');

      dayCard.innerHTML = `
        <div>
          <div class="day-num">Day ${day.day}</div>
          <div class="day-title">${day.title}</div>
        </div>
        <div class="lesson-stds-list" style="margin-top: 10px;">
          ${stdPills || '<span class="text-secondary" style="font-size:0.75rem;">No direct standards</span>'}
        </div>
      `;

      dayGrid.appendChild(dayCard);
    });

    // Append everything
    detailsPanel.appendChild(dayGrid);
    details.appendChild(summary);
    details.appendChild(detailsPanel);
    container.appendChild(details);
  });

  // Update totals count in UI
  const totalUnitsEl = document.getElementById('total-units-count');
  const totalDaysEl = document.getElementById('total-days-count');
  if (totalUnitsEl) totalUnitsEl.textContent = `${courseData.units.length} Units`;
  if (totalDaysEl) totalDaysEl.textContent = `${totalDays} Days`;
}

// Setup search filter functionality
function setupSearch() {
  const searchInput = document.getElementById('curriculum-search');
  if (!searchInput) return;

  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase().trim();
    const units = document.querySelectorAll('.unit-block');

    if (!query) {
      // Clear search highlights
      document.querySelectorAll('.day-card').forEach(card => {
        card.classList.remove('highlight-search');
        card.style.display = 'flex';
      });
      units.forEach(unit => {
        unit.style.display = 'block';
        unit.open = false; // close them back
      });
      return;
    }

    // Filter units and days
    units.forEach(unit => {
      let unitHasMatch = false;
      const dayCards = unit.querySelectorAll('.day-card');

      dayCards.forEach(card => {
        const text = card.dataset.searchText;
        if (text.includes(query)) {
          card.classList.add('highlight-search');
          card.style.display = 'flex';
          unitHasMatch = true;
        } else {
          card.classList.remove('highlight-search');
          card.style.display = 'none'; // hide non-matching days
        }
      });

      if (unitHasMatch) {
        unit.style.display = 'block';
        unit.open = true; // Auto-expand units with matches
      } else {
        unit.style.display = 'none'; // Hide units with zero matches
      }
    });
  });
}

// Setup course selector dropdown event listener
function setupCourseSelector() {
  const selectCourse = document.getElementById('select-course');
  if (!selectCourse) return;

  selectCourse.addEventListener('change', (e) => {
    activeCourse = e.target.value;
    
    // Update heading
    const titleEl = document.getElementById('curriculum-title');
    if (titleEl) {
      titleEl.textContent = activeCourse === 'acs_i'
        ? 'Advanced Computer Science I'
        : activeCourse === 'wdd_i'
          ? 'Web Development & Design I'
          : activeCourse === 'dgd_i'
            ? 'Digital Game Design I'
            : activeCourse === 'dgd_ii'
              ? 'Digital Game Design II (Bridge Year)'
              : 'Computer Education Technology';
    }

    // Clear search
    const searchInput = document.getElementById('curriculum-search');
    if (searchInput) searchInput.value = '';

    loadSyllabusData();
  });
}
