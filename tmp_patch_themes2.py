with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    src = f.read()

# ── Patch 1: Replace CSS section ──────────────────────────────────────────────
# Remove old pinned CSS, add new card variant CSS

OLD_CSS = '''.kt-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0;
  border-bottom: 2px solid var(--ink);
}
.kt-card {
  padding: 18px 16px;
  border-right: 1px solid var(--rule);
  border-bottom: 1px solid var(--rule);
  cursor: pointer;
  transition: background 0.15s;
  position: relative;
}
.kt-card:nth-child(5n) { border-right: none; }
.kt-card:hover { background: var(--paper-2); }
.kt-card.selected {
  background: var(--ink);
  color: var(--paper);
}
.kt-card.dimmed { opacity: 0.3; }
.kt-card-emoji { font-size: 22px; margin-bottom: 8px; line-height: 1; }
.kt-card-name {
  font-family: 'Playfair Display', serif;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.3;
  margin-bottom: 4px;
}
.kt-card.selected .kt-card-name { color: var(--paper); }
.kt-card-count {
  font-size: 10px;
  color: var(--ink-3);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.kt-card.selected .kt-card-count { color: rgba(255,255,255,0.5); }
.kt-selected-arrow {
  display: none;
  position: absolute;
  bottom: -12px;
  left: 50%;
  transform: translateX(-50%);
  width: 0; height: 0;
  border-left: 10px solid transparent;
  border-right: 10px solid transparent;
  border-top: 10px solid var(--ink);
  z-index: 5;
}
.kt-card.selected .kt-selected-arrow { display: block; }'''

NEW_CSS = '''.kt-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0;
  border-bottom: 2px solid var(--ink);
}
.kt-card {
  padding: 18px 16px;
  border-right: 1px solid var(--rule);
  border-bottom: 1px solid var(--rule);
  cursor: pointer;
  transition: background 0.15s;
  position: relative;
}
.kt-card:nth-child(5n) { border-right: none; }
.kt-card:hover { background: var(--paper-2); }
.kt-card.selected {
  background: var(--ink);
  color: var(--paper);
}
.kt-card.dimmed { opacity: 0.3; }

/* Gold permanent cards */
.kt-card.permanent {
  border-top: 3px solid var(--gold);
  background: var(--gold-bg);
}
.kt-card.permanent:hover { background: #ede3c8; }
.kt-card.permanent.selected { background: var(--ink); border-top-color: var(--gold); }
.kt-permanent-badge {
  position: absolute;
  top: 6px; right: 8px;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: var(--gold);
  opacity: 0.8;
}
.kt-card.selected .kt-permanent-badge { color: rgba(255,210,100,0.8); }
.kt-star-btn {
  position: absolute;
  bottom: 8px; right: 8px;
  font-size: 13px;
  background: none;
  border: none;
  cursor: pointer;
  opacity: 0.35;
  padding: 0;
  line-height: 1;
  transition: opacity 0.15s;
}
.kt-star-btn:hover { opacity: 1; }
.kt-card.permanent .kt-star-btn { opacity: 0.8; color: var(--gold); }
.kt-card.selected .kt-star-btn { opacity: 0.5; color: var(--paper); }
.kt-card.permanent.selected .kt-star-btn { color: #ffd264; opacity: 0.9; }

/* Silver manual cards */
.kt-card.manual {
  border: 1.5px dashed #9aa0aa;
  background: transparent;
  cursor: pointer;
}
.kt-card.manual:hover { background: var(--paper-2); }
.kt-card.manual.selected { background: var(--ink); border-style: solid; border-color: var(--ink); }
.kt-manual-badge {
  position: absolute;
  top: 6px; right: 8px;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: #7a8290;
  opacity: 0.8;
}
.kt-card.manual .kt-card-name { color: var(--ink-3); font-style: italic; }
.kt-card.manual.has-content .kt-card-name { color: var(--ink); font-style: normal; }
.kt-card.manual.selected .kt-card-name { color: var(--paper); }
.kt-card.manual .kt-card-count { color: #9aa0aa; }
.kt-card.manual.selected .kt-card-count { color: rgba(255,255,255,0.4); }

.kt-card-emoji { font-size: 22px; margin-bottom: 8px; line-height: 1; }
.kt-card-name {
  font-family: 'Playfair Display', serif;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.3;
  margin-bottom: 4px;
}
.kt-card.selected .kt-card-name { color: var(--paper); }
.kt-card-count {
  font-size: 10px;
  color: var(--ink-3);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.kt-card.selected .kt-card-count { color: rgba(255,255,255,0.5); }
.kt-selected-arrow {
  display: none;
  position: absolute;
  bottom: -12px;
  left: 50%;
  transform: translateX(-50%);
  width: 0; height: 0;
  border-left: 10px solid transparent;
  border-right: 10px solid transparent;
  border-top: 10px solid var(--ink);
  z-index: 5;
}
.kt-card.selected .kt-selected-arrow { display: block; }

/* Manual theme add modal */
.kt-manual-modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.45);
  z-index: 200;
  display: flex; align-items: center; justify-content: center;
}
.kt-manual-modal {
  background: var(--paper);
  border: 2px solid var(--ink);
  padding: 28px 32px;
  width: 420px;
  max-width: 90vw;
}
.kt-manual-modal-title {
  font-family: 'Playfair Display', serif;
  font-size: 17px;
  font-weight: 700;
  margin-bottom: 6px;
}
.kt-manual-modal-sub {
  font-size: 12px;
  color: var(--ink-3);
  margin-bottom: 18px;
  line-height: 1.5;
}
.kt-manual-modal label {
  display: block;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--ink-3);
  margin-bottom: 5px;
}
.kt-manual-modal input, .kt-manual-modal textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  border: 1px solid var(--rule);
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 13px;
  background: var(--paper-2);
  color: var(--ink);
  outline: none;
  margin-bottom: 14px;
}
.kt-manual-modal input:focus, .kt-manual-modal textarea:focus {
  border-color: #9aa0aa;
}
.kt-manual-modal-btns {
  display: flex; gap: 8px; justify-content: flex-end; margin-top: 4px;
}
.kt-manual-save-btn {
  padding: 8px 18px;
  background: var(--ink);
  color: var(--paper);
  border: none;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.kt-manual-cancel-btn {
  padding: 8px 14px;
  background: none;
  border: 1px solid var(--rule);
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 12px;
  color: var(--ink-3);
  cursor: pointer;
}'''

# ── Patch 2: Replace entire pinned + renderThemeGrid block ───────────────────

OLD_JS = '''// ── Pinned Topics ─────────────────────────────────────────────────────────
let pinnedTopics = JSON.parse(localStorage.getItem('meridian_pinned_topics') || '[]');
let ktPinInputVisible = false;

function savePinnedTopics() {
  localStorage.setItem('meridian_pinned_topics', JSON.stringify(pinnedTopics));
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
  const newName = prompt('Rename pinned topic:', oldName);
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
    const clickAction = hasMatch ? `selectTheme(${themeIdx})` : `renamePinnedTopic('${name.replace(/'/g, "\\\\'")}')`;
    return `<div class="kt-pinned-card${hasMatch?'':' no-match'}" onclick="${clickAction}" title="${hasMatch?'Open theme':('No matching theme — click to rename')}">
      <span class="kt-pinned-card-name">📌 ${name}</span>
      <button class="kt-pinned-card-unpin" onclick="event.stopPropagation(); removePinnedTopic('${name.replace(/'/g, "\\\\'")}')">✕</button>
    </div>`;
  }).join('');

  const inputHTML = ktPinInputVisible
    ? `<div class="kt-pin-input-wrap">
        <input class="kt-pin-input" id="kt-pin-input" type="text" placeholder="e.g. US-Iran Conflict" maxlength="50"
          onkeydown="if(event.key==='Enter'){addPinnedTopic(this.value)}" autofocus />
        <button class="kt-pin-save-btn" onclick="addPinnedTopic(document.getElementById('kt-pin-input').value)">Pin</button>
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
  const body = document.getElementById('kt-body');
  if (!ktThemes) return;

  // Match articles to themes using getThemeArticles if available, else fallback
  const themeArticles = ktThemes.map(theme => getThemeArticles ? getThemeArticles(theme) : articles.filter(a => {
    const kws = (theme.keywords || []).map(k => k.toLowerCase());
    const tags = (a.tags || []).map(t => t.toLowerCase());
    const topic = (a.topic || '').toLowerCase();
    return kws.some(k => tags.some(t => t.includes(k) || k.includes(t)) || topic.includes(k));
  }));

  const gridHTML = ktThemes.map((theme, i) => {
    const count = themeArticles[i].length;
    const isSelected = ktSelectedIdx === i;
    const isDimmed = ktSelectedIdx !== null && !isSelected;
    return `
      <div class="kt-card${isSelected?' selected':''}" onclick="selectTheme(${i})">
        <div class="kt-card-emoji">${theme.emoji || '📌'}</div>
        <div class="kt-card-name">${theme.name}</div>
        <div class="kt-card-count">${count} article${count!==1?'s':''}</div>
        <div class="kt-selected-arrow"></div>
      </div>`;
  }).join('');

  const detailHTML = ktSelectedIdx !== null ? renderThemeDetail(ktSelectedIdx, themeArticles[ktSelectedIdx]) : '';

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
    setTimeout(() => { const el = document.getElementById('kt-pin-input'); if (el) el.focus(); }, 50);
  }
}'''

NEW_JS = '''// ── Theme state: permanent (gold) + manual (silver) ──────────────────────
// permanentThemes: Set of theme names marked permanent by user
// manualThemes: Array of {name, keywords, emoji} user-defined entries (max 2)
let permanentThemes = new Set(JSON.parse(localStorage.getItem('meridian_permanent_themes') || '[]'));
let manualThemes = JSON.parse(localStorage.getItem('meridian_manual_themes') || '[]');
let ktManualModalSlot = null; // which slot (0 or 1) is being edited

function savePermanentThemes() {
  localStorage.setItem('meridian_permanent_themes', JSON.stringify([...permanentThemes]));
}
function saveManualThemes() {
  localStorage.setItem('meridian_manual_themes', JSON.stringify(manualThemes));
}

function togglePermanent(themeName, event) {
  event.stopPropagation();
  if (permanentThemes.has(themeName)) {
    permanentThemes.delete(themeName);
  } else {
    permanentThemes.add(themeName);
  }
  savePermanentThemes();
  renderThemeGrid();
}

function openManualModal(slot) {
  ktManualModalSlot = slot;
  const existing = manualThemes[slot];
  const overlay = document.createElement('div');
  overlay.className = 'kt-manual-modal-overlay';
  overlay.id = 'kt-manual-overlay';
  overlay.innerHTML = `
    <div class="kt-manual-modal">
      <div class="kt-manual-modal-title">Add Manual Theme</div>
      <div class="kt-manual-modal-sub">Define a custom theme. Articles are matched using your keywords against titles, tags and topics.</div>
      <label>Theme Name</label>
      <input id="kt-manual-name" type="text" placeholder="e.g. US-Iran Conflict" maxlength="60"
        value="${existing ? existing.name : ''}" />
      <label>Keywords <span style="font-weight:400;text-transform:none;letter-spacing:0">(comma-separated)</span></label>
      <input id="kt-manual-kw" type="text" placeholder="e.g. Iran, IRGC, Hormuz, sanctions, airstrike"
        value="${existing ? (existing.keywords||[]).join(', ') : ''}" />
      <label>Emoji <span style="font-weight:400;text-transform:none;letter-spacing:0">(optional)</span></label>
      <input id="kt-manual-emoji" type="text" placeholder="🎯" maxlength="4"
        value="${existing ? (existing.emoji||'') : ''}" style="width:70px;margin-bottom:18px" />
      <div class="kt-manual-modal-btns">
        ${existing ? `<button class="kt-manual-cancel-btn" onclick="removeManualTheme(${slot})" style="color:#c0392b;border-color:#c0392b;margin-right:auto">Remove</button>` : ''}
        <button class="kt-manual-cancel-btn" onclick="closeManualModal()">Cancel</button>
        <button class="kt-manual-save-btn" onclick="saveManualTheme()">Save Theme</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  setTimeout(() => document.getElementById('kt-manual-name').focus(), 50);
}

function closeManualModal() {
  const el = document.getElementById('kt-manual-overlay');
  if (el) el.remove();
  ktManualModalSlot = null;
}

function saveManualTheme() {
  const name = (document.getElementById('kt-manual-name').value || '').trim();
  if (!name) return;
  const kwRaw = (document.getElementById('kt-manual-kw').value || '').trim();
  const keywords = kwRaw ? kwRaw.split(',').map(k => k.trim()).filter(Boolean) : [name];
  const emoji = (document.getElementById('kt-manual-emoji').value || '').trim() || '🎯';
  const slot = ktManualModalSlot ?? 0;
  manualThemes[slot] = { name, keywords, emoji };
  saveManualThemes();
  // Also mark as permanent by default
  permanentThemes.add(name);
  savePermanentThemes();
  closeManualModal();
  renderThemeGrid();
}

function removeManualTheme(slot) {
  const theme = manualThemes[slot];
  if (theme) permanentThemes.delete(theme.name);
  manualThemes.splice(slot, 1);
  saveManualThemes();
  savePermanentThemes();
  closeManualModal();
  renderThemeGrid();
}

function getManualThemeArticles(theme) {
  if (!articles || !theme.keywords) return [];
  const kws = theme.keywords.map(k => k.toLowerCase());
  return articles.filter(a => {
    const title = (a.title || '').toLowerCase();
    const tags = (a.tags || []).map(t => t.toLowerCase());
    const topic = (a.topic || '').toLowerCase();
    const summary = (a.summary || '').toLowerCase();
    return kws.some(k => title.includes(k) || topic.includes(k) || summary.includes(k) ||
      tags.some(t => t.includes(k) || k.includes(t)));
  });
}

function renderThemeGrid() {
  const body = document.getElementById('kt-body');
  if (!ktThemes) return;

  // Build combined theme list: AI themes sorted by article_count desc, then manual slots
  const aiThemes = [...ktThemes].sort((a, b) => (b.article_count || 0) - (a.article_count || 0));

  // Match articles for AI themes
  const aiArticles = aiThemes.map(theme =>
    typeof getThemeArticles === 'function' ? getThemeArticles(theme) : []
  );

  // Re-sort by matched article count (getThemeArticles may differ from stored article_count)
  const aiPaired = aiThemes.map((t, i) => ({ theme: t, arts: aiArticles[i] }))
    .sort((a, b) => b.arts.length - a.arts.length);

  // Build AI card HTML
  const aiGridHTML = aiPaired.map(({ theme, arts }, i) => {
    const count = arts.length;
    // Find real index in ktThemes for selectTheme
    const realIdx = ktThemes.findIndex(t => t.name === theme.name);
    const isSelected = ktSelectedIdx === realIdx;
    const isDimmed = ktSelectedIdx !== null && !isSelected;
    const isPermanent = permanentThemes.has(theme.name);
    const starLabel = isPermanent ? '★' : '☆';
    const nameEsc = theme.name.replace(/'/g, "\\'");
    return `
      <div class="kt-card${isPermanent?' permanent':''}${isSelected?' selected':''}${isDimmed?' dimmed':''}"
           onclick="selectTheme(${realIdx})">
        ${isPermanent ? '<div class="kt-permanent-badge">Permanent</div>' : ''}
        <div class="kt-card-emoji">${theme.emoji || '📌'}</div>
        <div class="kt-card-name">${theme.name}</div>
        <div class="kt-card-count">${count} article${count!==1?'s':''}</div>
        <button class="kt-star-btn" onclick="togglePermanent('${nameEsc}', event)" title="${isPermanent?'Remove permanent status':'Mark as permanent'}">
          ${starLabel}
        </button>
        <div class="kt-selected-arrow"></div>
      </div>`;
  }).join('');

  // Build 2 manual slots (always show both, fill from manualThemes array)
  const manualGridHTML = [0, 1].map(slot => {
    const mt = manualThemes[slot];
    if (mt) {
      // Filled manual slot
      const arts = getManualThemeArticles(mt);
      const count = arts.length;
      // Find if it's in ktThemes as selected (it won't be, but handle gracefully)
      const isSelected = ktSelectedIdx === -(slot + 1); // use negative index convention
      const isDimmed = ktSelectedIdx !== null && !isSelected;
      return `
        <div class="kt-card manual has-content${isSelected?' selected':''}${isDimmed?' dimmed':''}"
             onclick="selectManualTheme(${slot})">
          <div class="kt-manual-badge">Manual</div>
          <div class="kt-card-emoji">${mt.emoji || '🎯'}</div>
          <div class="kt-card-name">${mt.name}</div>
          <div class="kt-card-count">${count} article${count!==1?'s':''}</div>
          <button class="kt-star-btn" onclick="event.stopPropagation(); openManualModal(${slot})" title="Edit theme" style="font-size:11px;opacity:0.4">✎</button>
          <div class="kt-selected-arrow"></div>
        </div>`;
    } else {
      // Empty manual slot
      return `
        <div class="kt-card manual" onclick="openManualModal(${slot})">
          <div class="kt-manual-badge">Manual</div>
          <div class="kt-card-emoji" style="opacity:0.3;font-size:18px">＋</div>
          <div class="kt-card-name" style="font-size:12px">Add custom theme</div>
          <div class="kt-card-count" style="opacity:0.5">click to define</div>
        </div>`;
    }
  }).join('');

  // Selected detail: AI theme or manual theme
  let detailHTML = '';
  if (ktSelectedIdx !== null && ktSelectedIdx >= 0) {
    const realTheme = ktThemes[ktSelectedIdx];
    const realArts = typeof getThemeArticles === 'function' ? getThemeArticles(realTheme) : [];
    detailHTML = renderThemeDetail(ktSelectedIdx, realArts);
  } else if (ktSelectedIdx !== null && ktSelectedIdx < 0) {
    const slot = -(ktSelectedIdx + 1);
    const mt = manualThemes[slot];
    if (mt) {
      const arts = getManualThemeArticles(mt);
      detailHTML = renderManualThemeDetail(mt, arts);
    }
  }

  // Count permanent themes
  const permCount = [...permanentThemes].filter(n =>
    ktThemes.some(t => t.name === n) || manualThemes.some(m => m && m.name === n)
  ).length;
  const manualCount = manualThemes.filter(Boolean).length;
  const extraNote = (permCount || manualCount)
    ? ` · <span style="color:var(--gold);font-size:10px">★ ${permCount} permanent</span>${manualCount ? ` · <span style="color:#7a8290;font-size:10px">✎ ${manualCount} manual</span>` : ''}`
    : '';

  body.innerHTML = `
    <div class="kt-header">
      <div>
        <div class="kt-header-title">Intelligence Themes</div>
        <div class="kt-header-sub">${articles.length} articles across ${ktThemes.length} themes${extraNote}</div>
      </div>
      <button class="kt-regenerate-btn" onclick="generateThemes(true)">↺ Reset Themes</button>
    </div>
    <div class="kt-grid">${aiGridHTML}${manualGridHTML}</div>
    ${detailHTML}`;
}

function selectManualTheme(slot) {
  const newIdx = -(slot + 1);
  ktSelectedIdx = ktSelectedIdx === newIdx ? null : newIdx;
  renderThemeGrid();
  if (ktSelectedIdx !== null) {
    setTimeout(() => {
      const divider = document.querySelector('.kt-divider');
      if (divider) divider.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 50);
  }
}

function renderManualThemeDetail(theme, arts) {
  // Simplified detail panel for manual themes — reuses existing detail styles
  const sourceMap = {};
  arts.forEach(a => { sourceMap[a.source] = (sourceMap[a.source]||0)+1; });
  const sourceHTML = Object.entries(sourceMap)
    .sort((a,b) => b[1]-a[1])
    .map(([s,n]) => `<span class="source-pill">${s} (${n})</span>`).join('');
  const artListHTML = arts.slice(0,30).map(a =>
    `<div class="kt-art-item" onclick="openArticleById('${a.id}')">
      <div class="kt-art-title">${a.title}</div>
      <div class="kt-art-meta">${a.source}${a.pub_date?' · '+a.pub_date:''}</div>
    </div>`).join('');
  return `<div class="kt-divider"></div>
    <div class="kt-detail">
      <div class="kt-detail-header">
        <div>
          <div class="kt-detail-emoji">${theme.emoji||'🎯'}</div>
          <div class="kt-detail-name">${theme.name}</div>
          <div class="kt-detail-meta">${arts.length} articles · <span style="color:#7a8290;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Manual Theme</span></div>
          <div style="margin-top:6px;font-size:11px;color:var(--ink-3)">Keywords: ${(theme.keywords||[]).join(', ')}</div>
        </div>
        <button class="kt-detail-close" onclick="ktSelectedIdx=null;renderThemeGrid()">✕</button>
      </div>
      <div style="padding:12px 20px 6px;display:flex;gap:6px;flex-wrap:wrap">${sourceHTML}</div>
      <div class="kt-art-list">${artListHTML || '<div style="padding:20px;color:var(--ink-3);font-size:13px">No articles matched these keywords yet.</div>'}</div>
    </div>`;
}'''

results = []

if OLD_CSS in src:
    src = src.replace(OLD_CSS, NEW_CSS)
    results.append("CSS patch: OK")
else:
    results.append("CSS patch: FAILED")

if OLD_JS in src:
    src = src.replace(OLD_JS, NEW_JS)
    results.append("JS patch: OK")
else:
    results.append("JS patch: FAILED")

with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(src)

for r in results:
    print(r)
