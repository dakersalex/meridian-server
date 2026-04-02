with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    src = f.read()

# ── Patch 1: Add CSS for pinned topic row ──────────────────────────────────
OLD_CSS = '.kt-regenerate-btn:hover { border-color: var(--accent); color: var(--accent); }'

NEW_CSS = '''.kt-regenerate-btn:hover { border-color: var(--accent); color: var(--accent); }

.kt-pinned-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--rule);
  flex-wrap: wrap;
}
.kt-pinned-label {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--gold);
  white-space: nowrap;
  padding-right: 4px;
}
.kt-pinned-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px 7px 14px;
  border: 1.5px solid var(--gold);
  background: var(--gold-bg);
  border-radius: 2px;
  cursor: pointer;
  transition: all 0.15s;
  position: relative;
}
.kt-pinned-card:hover { background: #e8d9a8; }
.kt-pinned-card.no-match { opacity: 0.55; cursor: default; }
.kt-pinned-card-name {
  font-family: \'Playfair Display\', serif;
  font-size: 12px;
  font-weight: 600;
  color: var(--gold);
  line-height: 1.2;
}
.kt-pinned-card-unpin {
  font-size: 11px;
  color: var(--gold);
  opacity: 0.6;
  line-height: 1;
  padding: 0 2px;
  border: none;
  background: none;
  cursor: pointer;
}
.kt-pinned-card-unpin:hover { opacity: 1; }
.kt-pin-add-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 11px;
  border: 1.5px dashed var(--gold);
  background: transparent;
  border-radius: 2px;
  font-size: 11px;
  color: var(--gold);
  cursor: pointer;
  font-family: \'IBM Plex Sans\', sans-serif;
  opacity: 0.7;
  transition: opacity 0.15s;
}
.kt-pin-add-btn:hover { opacity: 1; }
.kt-pin-input-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}
.kt-pin-input {
  padding: 5px 9px;
  border: 1.5px solid var(--gold);
  border-radius: 2px;
  font-family: \'IBM Plex Sans\', sans-serif;
  font-size: 12px;
  background: var(--gold-bg);
  color: var(--ink);
  outline: none;
  width: 180px;
}
.kt-pin-save-btn {
  padding: 5px 10px;
  background: var(--gold);
  color: var(--paper);
  border: none;
  border-radius: 2px;
  font-size: 11px;
  font-family: \'IBM Plex Sans\', sans-serif;
  cursor: pointer;
  font-weight: 600;
}
.kt-pin-cancel-btn {
  padding: 5px 8px;
  background: none;
  border: 1px solid var(--rule);
  border-radius: 2px;
  font-size: 11px;
  font-family: \'IBM Plex Sans\', sans-serif;
  cursor: pointer;
  color: var(--ink-3);
}'''

# ── Patch 2: Replace renderThemeGrid with pinned-aware version ────────────
OLD_RENDER = '''function renderThemeGrid() {
  const body = document.getElementById(\'kt-body\');
  if (!ktThemes) return;

  // Match articles to themes
  const themeArticles = ktThemes.map(theme => {
    const kws = (theme.keywords || []).map(k => k.toLowerCase());
    return articles.filter(a => {
      const tags = (a.tags || []).map(t => t.toLowerCase());
      const topic = (a.topic || \'\').toLowerCase();
      return kws.some(k => tags.some(t => t.includes(k) || k.includes(t)) || topic.includes(k));
    });
  });

  const gridHTML = ktThemes.map((theme, i) => {
    const count = themeArticles[i].length;
    const isSelected = ktSelectedIdx === i;
    const isDimmed = ktSelectedIdx !== null && !isSelected;
    return `
      <div class="kt-card${isSelected?\' selected\':\'\'}" onclick="selectTheme(${i})">
        <div class="kt-card-emoji">${theme.emoji || \'📌\'}</div>
        <div class="kt-card-name">${theme.name}</div>
        <div class="kt-card-count">${count} article${count!==1?\'s\':\'\'}</div>
        <div class="kt-selected-arrow"></div>
      </div>`;
  }).join(\'\');

  const detailHTML = ktSelectedIdx !== null ? renderThemeDetail(ktSelectedIdx, themeArticles[ktSelectedIdx]) : \'\';

  body.innerHTML = `
    <div class="kt-header">
      <div>
        <div class="kt-header-title">Intelligence Themes</div>
        <div class="kt-header-sub">${articles.length} articles across ${ktThemes.length} themes</div>
      </div>
      <button class="kt-regenerate-btn" onclick="generateThemes(true)">↺ Reset Themes</button>
    </div>
    <div class="kt-grid">${gridHTML}</div>
    ${detailHTML}`;
}'''

NEW_RENDER = '''// ── Pinned Topics ─────────────────────────────────────────────────────────
let pinnedTopics = JSON.parse(localStorage.getItem(\'meridian_pinned_topics\') || \'[]\');
let ktPinInputVisible = false;

function savePinnedTopics() {
  localStorage.setItem(\'meridian_pinned_topics\', JSON.stringify(pinnedTopics));
}

function addPinnedTopic(name) {
  name = name.trim();
  if (!name || pinnedTopics.includes(name)) return;
  pinnedTopics.push(name);
  savePinnedTopics();
  ktPinInputVisible = false;
  renderThemeGrid();
}

function removePinnedTopic(name) {
  pinnedTopics = pinnedTopics.filter(p => p !== name);
  savePinnedTopics();
  renderThemeGrid();
}

function renamePinnedTopic(oldName) {
  const newName = prompt(\'Rename pinned topic:\', oldName);
  if (!newName || newName.trim() === oldName) return;
  const idx = pinnedTopics.indexOf(oldName);
  if (idx !== -1) {
    pinnedTopics[idx] = newName.trim();
    savePinnedTopics();
    renderThemeGrid();
  }
}

function findMatchingThemeIdx(pinnedName) {
  if (!ktThemes) return -1;
  const pn = pinnedName.toLowerCase();
  // Exact match first
  let idx = ktThemes.findIndex(t => t.name.toLowerCase() === pn);
  if (idx !== -1) return idx;
  // Partial match: pinned name words appear in theme name or vice versa
  const pWords = pn.split(/\\s+/).filter(w => w.length > 3);
  idx = ktThemes.findIndex(t => {
    const tn = t.name.toLowerCase();
    return pWords.some(w => tn.includes(w)) || tn.split(/\\s+/).filter(w => w.length > 3).some(w => pn.includes(w));
  });
  return idx;
}

function renderPinnedRow() {
  if (pinnedTopics.length === 0 && !ktPinInputVisible) {
    return `<div class="kt-pinned-row">
      <button class="kt-pin-add-btn" onclick="ktPinInputVisible=true; renderThemeGrid()">⊕ Pin a topic</button>
    </div>`;
  }

  const pinnedCardsHTML = pinnedTopics.map(name => {
    const themeIdx = findMatchingThemeIdx(name);
    const hasMatch = themeIdx !== -1;
    const clickAction = hasMatch ? `selectTheme(${themeIdx})` : `renamePinnedTopic(\'${name.replace(/\'/g, "\\\\\'")}\')`;
    return `<div class="kt-pinned-card${hasMatch?\'\':' no-match'}" onclick="${clickAction}" title="${hasMatch?\'Open theme\':(\'No matching theme — click to rename\')}">
      <span class="kt-pinned-card-name">📌 ${name}</span>
      <button class="kt-pinned-card-unpin" onclick="event.stopPropagation(); removePinnedTopic(\'${name.replace(/\'/g, "\\\\\'")}\')">✕</button>
    </div>`;
  }).join(\'\');

  const inputHTML = ktPinInputVisible
    ? `<div class="kt-pin-input-wrap">
        <input class="kt-pin-input" id="kt-pin-input" type="text" placeholder="e.g. US-Iran Conflict" maxlength="50"
          onkeydown="if(event.key===\'Enter\'){addPinnedTopic(this.value)}" autofocus />
        <button class="kt-pin-save-btn" onclick="addPinnedTopic(document.getElementById(\'kt-pin-input\').value)">Pin</button>
        <button class="kt-pin-cancel-btn" onclick="ktPinInputVisible=false; renderThemeGrid()">Cancel</button>
      </div>`
    : `<button class="kt-pin-add-btn" onclick="ktPinInputVisible=true; renderThemeGrid()">⊕ Pin a topic</button>`;

  return `<div class="kt-pinned-row">
    <span class="kt-pinned-label">Pinned</span>
    ${pinnedCardsHTML}
    ${inputHTML}
  </div>`;
}

function renderThemeGrid() {
  const body = document.getElementById(\'kt-body\');
  if (!ktThemes) return;

  // Match articles to themes using getThemeArticles if available, else fallback
  const themeArticles = ktThemes.map(theme => getThemeArticles ? getThemeArticles(theme) : articles.filter(a => {
    const kws = (theme.keywords || []).map(k => k.toLowerCase());
    const tags = (a.tags || []).map(t => t.toLowerCase());
    const topic = (a.topic || \'\').toLowerCase();
    return kws.some(k => tags.some(t => t.includes(k) || k.includes(t)) || topic.includes(k));
  }));

  const gridHTML = ktThemes.map((theme, i) => {
    const count = themeArticles[i].length;
    const isSelected = ktSelectedIdx === i;
    const isDimmed = ktSelectedIdx !== null && !isSelected;
    return `
      <div class="kt-card${isSelected?\' selected\':\'\'}" onclick="selectTheme(${i})">
        <div class="kt-card-emoji">${theme.emoji || \'📌\'}</div>
        <div class="kt-card-name">${theme.name}</div>
        <div class="kt-card-count">${count} article${count!==1?\'s\':\'\'}</div>
        <div class="kt-selected-arrow"></div>
      </div>`;
  }).join(\'\');

  const detailHTML = ktSelectedIdx !== null ? renderThemeDetail(ktSelectedIdx, themeArticles[ktSelectedIdx]) : \'\';

  body.innerHTML = `
    <div class="kt-header">
      <div>
        <div class="kt-header-title">Intelligence Themes</div>
        <div class="kt-header-sub">${articles.length} articles across ${ktThemes.length} themes</div>
      </div>
      <button class="kt-regenerate-btn" onclick="generateThemes(true)">↺ Reset Themes</button>
    </div>
    ${renderPinnedRow()}
    <div class="kt-grid">${gridHTML}</div>
    ${detailHTML}`;

  // Focus pin input if just opened
  if (ktPinInputVisible) {
    setTimeout(() => { const el = document.getElementById(\'kt-pin-input\'); if (el) el.focus(); }, 50);
  }
}'''

results = []

if OLD_CSS in src:
    src = src.replace(OLD_CSS, NEW_CSS)
    results.append("Patch 1 (CSS): OK")
else:
    results.append("Patch 1 (CSS): FAILED")

# The OLD_RENDER has dynamic content with isDimmed — check for the simpler unique anchor
OLD_RENDER_ANCHOR = "function renderThemeGrid() {\n  const body = document.getElementById('kt-body');\n  if (!ktThemes) return;\n\n  // Match articles to themes\n  const themeArticles = ktThemes.map(theme => {"
if OLD_RENDER_ANCHOR in src:
    # Find full function and replace
    start = src.find(OLD_RENDER_ANCHOR)
    # Find the closing of the function - look for the next top-level function after
    end_marker = "\nfunction selectTheme("
    end = src.find(end_marker, start)
    if end != -1:
        old_block = src[start:end]
        src = src[:start] + NEW_RENDER + src[end:]
        results.append(f"Patch 2 (renderThemeGrid): OK (replaced {len(old_block)} chars)")
    else:
        results.append("Patch 2 (renderThemeGrid): FAILED - end marker not found")
else:
    results.append("Patch 2 (renderThemeGrid): FAILED - start anchor not found")

with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(src)

for r in results:
    print(r)
