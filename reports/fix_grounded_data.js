const fs = require('fs');
const path = require('path');

const vaultPath = '/Users/willbumgardner/Desktop/TheVault';
const txtFile = path.join(vaultPath, 'reports/nv_cs_standards.txt');
const outJsonStandards = path.join(vaultPath, 'reports/nv_cs_standards_grounded.json');

// ==========================================
// 1. PARSE NV STANDARDS
// ==========================================

const lines = fs.readFileSync(txtFile, 'utf-8').split(/\r?\n/);
const contentStandards = {};
let currentContent = '';
let currentPerf = '';

let i = 0;
while (i < lines.length) {
  const line = lines[i].trim();
  
  if (i > 400 && (line.includes('Complementary Courses') || line.includes('State Complementary Skill Standards'))) {
    console.log(`Reached Complementary Courses section at line ${i+1}. Stopping standards parser.`);
    break;
  }
  
  // Content Standard Header
  const mContent = line.match(/^CONTENT STANDARD (\d+\.\d+):\s*(.+)$/);
  if (mContent) {
    const num = mContent[1];
    const name = mContent[2].trim();
    currentContent = num;
    contentStandards[num] = {
      title: name,
      performance_standards: {}
    };
    i++;
    continue;
  }
  
  // Performance Standard Header
  const mPerf = line.match(/^Performance Standard (\d+\.\d+):\s*(.+)$/);
  if (mPerf) {
    const num = mPerf[1];
    const name = mPerf[2].trim();
    currentPerf = num;
    const contentNum = num.split('.')[0] + '.0';
    if (contentStandards[contentNum]) {
      contentStandards[contentNum].performance_standards[num] = {
        title: name,
        indicators: {}
      };
    }
    i++;
    continue;
  }
  
  // Performance Indicator Start
  const mInd = line.match(/^(\d+\.\d+\.\d+)\s+(.+)$/);
  if (mInd) {
    const code = mInd[1];
    const firstLineText = mInd[2].trim();
    
    const textParts = [firstLineText];
    let j = i + 1;
    let level = null;
    
    while (j < lines.length) {
      const nextLine = lines[j].trim();
      
      // Stop if new header or indicator
      if (
        nextLine.match(/^CONTENT STANDARD/) ||
        nextLine.match(/^Performance Standard/) ||
        nextLine.match(/^\d+\.\d+\.\d+/) ||
        nextLine.includes('Complementary Courses') ||
        nextLine.includes('State Complementary Skill Standards')
      ) {
        break;
      }
      
      // Skip empty, page numbers, or form feed
      if (!nextLine || /^\d+$/.test(nextLine) || nextLine.startsWith('\x0c')) {
        j++;
        continue;
      }
      
      textParts.push(nextLine);
      
      // Check for level tag at end of line (nested parentheses support)
      const mLevel = nextLine.match(/\((?:[^()]+|\([^()]*\))*\)\s*$/);
      if (mLevel) {
        const levelStr = mLevel[0].replace(/[()]/g, '');
        const levels = [];
        if (levelStr.includes('L1') || levelStr.includes('Level 1')) levels.push('L1');
        if (levelStr.includes('L2') || levelStr.includes('Level 2')) levels.push('L2');
        if (levelStr.includes('C') || levelStr.includes('Complementary')) levels.push('C');
        level = levels.length ? levels.join(', ') : levelStr;
        
        // Remove level tag from last part
        textParts[textParts.length - 1] = nextLine.substring(0, mLevel.index).trim();
        j++;
        break;
      }
      
      j++;
    }
    
    let description = textParts.join(' ').trim();
    description = description.replace(/\s+/g, ' ');
    
    if (!level) {
      const mLevel = description.match(/\((?:[^()]+|\([^()]*\))*\)\s*$/);
      if (mLevel) {
        const levelStr = mLevel[0].replace(/[()]/g, '');
        const levels = [];
        if (levelStr.includes('L1') || levelStr.includes('Level 1')) levels.push('L1');
        if (levelStr.includes('L2') || levelStr.includes('Level 2')) levels.push('L2');
        if (levelStr.includes('C') || levelStr.includes('Complementary')) levels.push('C');
        level = levels.length ? levels.join(', ') : levelStr;
        description = description.substring(0, mLevel.index).trim();
      } else {
        level = 'L1';
      }
    }
    
    // Clean trailing characters
    description = description.replace(/^[:\s\-*]+|[:\s\-*]+$/g, '');
    
    const contentNum = code.split('.')[0] + '.0';
    const perfNum = code.split('.').slice(0, 2).join('.');
    
    if (contentStandards[contentNum]) {
      if (contentStandards[contentNum].performance_standards[perfNum]) {
        contentStandards[contentNum].performance_standards[perfNum].indicators[code] = {
          description,
          level
        };
      }
    }
    
    i = j;
    continue;
  }
  
  i++;
}

fs.writeFileSync(outJsonStandards, JSON.stringify(contentStandards, null, 2), 'utf-8');
console.log(`1. Standards parsed: ${Object.keys(contentStandards).length} Content Standards written to ${outJsonStandards}`);


// ==========================================
// 2. EXTRACT CANONICAL COURSE MAP UNIT TITLES
// ==========================================

const reviewFile = path.join(vaultPath, '03_Teaching/ACS_I/ACS_I_Course_Review.md');
const unitTitles = {};
const reviewContent = fs.readFileSync(reviewFile, 'utf-8').split(/\r?\n/);

for (const line of reviewContent) {
  if (line.trim().startsWith('|')) {
    const cells = line.split('|').map(c => c.trim()).filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);
    if (cells.length >= 2) {
      const unitStr = cells[0];
      const titleCell = cells[1];
      if (/^\d+$/.test(unitStr)) {
        const unitNum = parseInt(unitStr, 10);
        let title = titleCell.replace(/\\\|/g, '|');
        const mWiki = title.match(/\[\[(?:[^|]+\|)?(.*?)\]\]/);
        if (mWiki) {
          title = mWiki[1];
        }
        title = title.replace(/\[\[/g, '').replace(/\]\]/g, '').trim();
        unitTitles[unitNum] = title;
      }
    }
  }
}

console.log(`2. Extracted ${Object.keys(unitTitles).length} canonical unit titles from course review.`);


// ==========================================
// 3. MERGE AND UPDATE COURSE MAP JSON
// ==========================================

const acsPath = path.join(vaultPath, '03_Teaching/ACS_I');
const courseData = {
  units: [],
  standards: {}
};

const flatStandardsMap = {};
for (const cCode in contentStandards) {
  for (const pCode in contentStandards[cCode].performance_standards) {
    for (const iCode in contentStandards[cCode].performance_standards[pCode].indicators) {
      flatStandardsMap[iCode] = contentStandards[cCode].performance_standards[pCode].indicators[iCode].description;
    }
  }
}

const dirNames = fs.readdirSync(acsPath).filter(name => {
  const dirPath = path.join(acsPath, name);
  return fs.statSync(dirPath).isDirectory() && /^ACS1 Unit \d+$/.test(name);
});

const unitDirs = dirNames.map(name => {
  const num = parseInt(name.match(/\d+/)[0], 10);
  return { num, dirPath: path.join(acsPath, name) };
});

unitDirs.sort((a, b) => a.num - b.num);

for (const { num, dirPath } of unitDirs) {
  const unitInfo = {
    number: num,
    title: unitTitles[num] || `Unit ${num}`,
    days: [],
    standards: []
  };
  
  const files = fs.readdirSync(dirPath).filter(f => f.endsWith('Lesson_Plan.md') && (f.includes('Day_') || f.includes('Day')));
  
  const getDayNum = (filename) => {
    const m = filename.match(/Day_(\d+)/);
    if (m) return parseInt(m[1], 10);
    const m2 = filename.match(/(\d+)/);
    return m2 ? parseInt(m2[1], 10) : 999;
  };
  
  files.sort((a, b) => getDayNum(a) - getDayNum(b));
  
  for (const file of files) {
    const filePath = path.join(dirPath, file);
    const dayNum = getDayNum(file);
    const dayContent = fs.readFileSync(filePath, 'utf-8');
    
    // Day Title
    let dayTitle = `Day ${dayNum}`;
    const dayTitleMatch = dayContent.match(/^#\s*(Unit\s*\d+\s*Day\s*\d+[:\s—\-]*|Day\s*\d+[:\s—\-]*)(.+)$/m);
    if (dayTitleMatch) {
      dayTitle = dayTitleMatch[2].trim();
    } else {
      const h1 = dayContent.match(/^#\s+(.+)$/m);
      if (h1) {
        dayTitle = h1[1].trim();
      }
    }
    
    dayTitle = dayTitle.replace(/\[\[.*?\|(.*?)\]\]/g, '$1').replace(/\[\[(.*?)\]\]/g, '$1');
    dayTitle = dayTitle.replace(/Lesson Plan/g, '').replace(/^[:\s\-*]+|[:\s\-*]+$/g, '').trim();
    
    // Standards
    const dayStds = [];
    const matches = dayContent.match(/ADVCS\.\d+\.\d+\.\d+/g) || [];
    for (const code of matches) {
      if (!dayStds.includes(code)) {
        dayStds.push(code);
      }
      if (!unitInfo.standards.includes(code)) {
        unitInfo.standards.push(code);
      }
    }
    
    unitInfo.days.push({
      day: dayNum,
      title: dayTitle,
      standards: dayStds
    });
  }
  
  courseData.units.push(unitInfo);
}

for (const code in flatStandardsMap) {
  courseData.standards[code] = flatStandardsMap[code] || 'Nevada Computer Science Standard';
}

const outJsonCourse = path.join(vaultPath, 'reports/acs1_course_map_grounded.json');
fs.writeFileSync(outJsonCourse, JSON.stringify(courseData, null, 2), 'utf-8');

console.log(`\n3. Course map data with canonical titles and merged standards written to ${outJsonCourse}!`);
console.log('Done fixing datasets!');
