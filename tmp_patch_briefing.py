with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    src = f.read()

results = []

# ── Patch 1: Add third folder tab in HTML ────────────────────────────────────
OLD_TABS = '''  <button class="folder-tab folder-tab-newsfeed" id="tab-newsfeed" onclick="switchMode(\'newsfeed\')">News Feed</button>
  <button class="folder-tab folder-tab-themes" id="tab-themes" onclick="switchMode(\'themes\')">Key Themes</button>
  <div class="folder-spacer"></div>'''

NEW_TABS = '''  <button class="folder-tab folder-tab-newsfeed" id="tab-newsfeed" onclick="switchMode(\'newsfeed\')">News Feed</button>
  <button class="folder-tab folder-tab-themes" id="tab-themes" onclick="switchMode(\'themes\')">Key Themes</button>
  <button class="folder-tab folder-tab-briefing" id="tab-briefing" onclick="switchMode(\'briefing\')">Briefing Generator</button>
  <div class="folder-spacer"></div>'''

if OLD_TABS in src:
    src = src.replace(OLD_TABS, NEW_TABS)
    results.append("Patch 1 (tab HTML): OK")
else:
    results.append("Patch 1 (tab HTML): FAILED")

# ── Patch 2: Add CSS for briefing tab + panel ────────────────────────────────
OLD_CSS_ANCHOR = '.folder-tab-newsfeed.inactive {'
NEW_CSS = '''.folder-tab-newsfeed.inactive {'''  # keep this, just insert before it

BRIEFING_CSS = '''
/* ── Briefing Generator tab ── */
.folder-tab-briefing {
  background: var(--paper-3);
  color: var(--ink-3);
  height: 28px;
  z-index: 1;
  position: relative;
  margin-left: 2px;
  border-bottom: none;
  box-shadow: 1px -2px 3px rgba(0,0,0,0.08);
}
.folder-tab-briefing.active {
  background: var(--accent);
  color: var(--paper);
  height: 34px;
  z-index: 3;
  border-bottom: 2.5px solid var(--accent);
  box-shadow: -2px -3px 5px rgba(0,0,0,0.18), 2px -3px 5px rgba(0,0,0,0.10);
}

/* ── Briefing Generator view ── */
#briefing-view {
  display: none;
  padding: 40px 0;
  max-width: 680px;
  margin: 0 auto;
}
#briefing-view.visible { display: block; }

.bg-section {
  margin-bottom: 28px;
}
.bg-section-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: var(--ink-3);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.bg-section-label span.bg-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px; height: 18px;
  border-radius: 50%;
  background: var(--ink);
  color: var(--paper);
  font-size: 9px;
  font-weight: 700;
  flex-shrink: 0;
}

/* Topic selector */
.bg-topic-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.bg-radio-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.bg-radio-row input[type=radio] { accent-color: var(--accent); width: 15px; height: 15px; cursor: pointer; }
.bg-radio-row label { font-size: 13px; color: var(--ink); cursor: pointer; }
.bg-theme-select {
  margin-left: 25px;
  margin-top: 4px;
  padding: 7px 10px;
  border: 1px solid var(--rule);
  background: var(--paper-2);
  font-family: \'IBM Plex Sans\', sans-serif;
  font-size: 12px;
  color: var(--ink);
  width: 100%;
  max-width: 360px;
  cursor: pointer;
  display: none;
}
.bg-focused-input {
  margin-left: 25px;
  margin-top: 6px;
  display: none;
  flex-direction: column;
  gap: 6px;
}
.bg-focused-input input {
  padding: 8px 10px;
  border: 1px solid var(--rule);
  background: var(--paper-2);
  font-family: \'IBM Plex Sans\', sans-serif;
  font-size: 13px;
  color: var(--ink);
  width: 100%;
  box-sizing: border-box;
  outline: none;
}
.bg-focused-input input:focus { border-color: var(--accent); }

.bg-guidance-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: var(--ink-3);
  margin-top: 2px;
}
.bg-guidance-textarea {
  padding: 8px 10px;
  border: 1px solid var(--rule);
  background: var(--paper-2);
  font-family: \'IBM Plex Sans\', sans-serif;
  font-size: 12px;
  color: var(--ink);
  width: 100%;
  box-sizing: border-box;
  resize: vertical;
  min-height: 64px;
  outline: none;
  line-height: 1.5;
}
.bg-guidance-textarea:focus { border-color: var(--accent); }
.bg-guidance-textarea::placeholder { color: var(--ink-3); font-style: italic; }

/* Time period */
.bg-period-btns {
  display: flex;
  gap: 0;
  border: 1.5px solid var(--rule);
  border-radius: 2px;
  overflow: hidden;
  width: fit-content;
}
.bg-period-btn {
  padding: 7px 18px;
  font-family: \'IBM Plex Sans\', sans-serif;
  font-size: 12px;
  font-weight: 500;
  background: var(--paper-2);
  color: var(--ink-3);
  border: none;
  border-right: 1px solid var(--rule);
  cursor: pointer;
  transition: all 0.12s;
}
.bg-period-btn:last-child { border-right: none; }
.bg-period-btn:hover { background: var(--paper-3); color: var(--ink); }
.bg-period-btn.active {
  background: var(--ink);
  color: var(--paper);
}

/* Brief type */
.bg-type-cards {
  display: flex;
  gap: 12px;
}
.bg-type-card {
  flex: 1;
  padding: 16px 18px;
  border: 1.5px solid var(--rule);
  background: var(--paper-2);
  cursor: pointer;
  transition: all 0.15s;
  position: relative;
}
.bg-type-card:hover { border-color: var(--ink-3); }
.bg-type-card.active {
  border-color: var(--ink);
  background: var(--paper);
  box-shadow: 0 1px 6px rgba(0,0,0,0.10);
}
.bg-type-card-icon { font-size: 18px; margin-bottom: 6px; }
.bg-type-card-name {
  font-family: \'Playfair Display\', serif;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 3px;
}
.bg-type-card-meta {
  font-size: 10px;
  color: var(--ink-3);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.bg-type-card.active .bg-type-card-meta { color: var(--ink-3); }
.bg-type-check {
  position: absolute;
  top: 10px; right: 12px;
  font-size: 14px;
  color: var(--accent);
  display: none;
}
.bg-type-card.active .bg-type-check { display: block; }

/* Article count preview */
.bg-article-preview {
  font-size: 11px;
  color: var(--ink-3);
  margin-top: 8px;
  min-height: 16px;
  font-style: italic;
}

/* Generate button */
.bg-generate-btn {
  width: 100%;
  padding: 14px;
  background: var(--accent);
  color: var(--paper);
  border: none;
  font-family: \'IBM Plex Sans\', sans-serif;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  letter-spacing: 0.3px;
  transition: opacity 0.15s;
  margin-top: 8px;
}
.bg-generate-btn:hover { opacity: 0.88; }
.bg-generate-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.bg-divider {
  border: none;
  border-top: 1px solid var(--rule);
  margin: 28px 0;
}
'''

if OLD_CSS_ANCHOR in src:
    src = src.replace(OLD_CSS_ANCHOR, BRIEFING_CSS + OLD_CSS_ANCHOR)
    results.append("Patch 2 (CSS): OK")
else:
    results.append("Patch 2 (CSS): FAILED")

# ── Patch 3: Add briefing panel HTML after key-themes-view div ───────────────
OLD_HTML_ANCHOR = '<!-- Brief modal -->'
BRIEFING_HTML = '''<!-- Briefing Generator view -->
<div id="briefing-view">
  <div style="font-family:\'Playfair Display\',serif;font-size:26px;font-weight:700;margin-bottom:6px">Briefing Generator</div>
  <div style="font-size:12px;color:var(--ink-3);margin-bottom:32px">Configure your brief below, then generate</div>

  <!-- 1. TOPIC -->
  <div class="bg-section">
    <div class="bg-section-label"><span class="bg-num">1</span> Topic</div>
    <div class="bg-topic-options">
      <div class="bg-radio-row">
        <input type="radio" name="bg-topic" id="bg-topic-all" value="all" checked onchange="bgUpdateTopic()">
        <label for="bg-topic-all">All themes — draw from entire library</label>
      </div>
      <div>
        <div class="bg-radio-row">
          <input type="radio" name="bg-topic" id="bg-topic-theme" value="theme" onchange="bgUpdateTopic()">
          <label for="bg-topic-theme">Select a theme</label>
        </div>
        <select class="bg-theme-select" id="bg-theme-select" onchange="bgUpdatePreview()">
          <option value="">— choose a theme —</option>
        </select>
      </div>
      <div>
        <div class="bg-radio-row">
          <input type="radio" name="bg-topic" id="bg-topic-focused" value="focused" onchange="bgUpdateTopic()">
          <label for="bg-topic-focused">Focused topic</label>
        </div>
        <div class="bg-focused-input" id="bg-focused-input">
          <input type="text" id="bg-focused-text" placeholder="e.g. Impact of Iran conflict on oil supply chains" maxlength="120"
            oninput="bgUpdatePreview()" />
          <div class="bg-guidance-label">Guidance</div>
          <textarea class="bg-guidance-textarea" id="bg-guidance-text"
            placeholder="Add any guidance for the AI to incorporate — e.g. focus on economic implications, include European perspective, highlight risks for energy markets…"
            oninput="bgUpdatePreview()"></textarea>
        </div>
      </div>
    </div>
  </div>

  <hr class="bg-divider">

  <!-- 2. TIME PERIOD -->
  <div class="bg-section">
    <div class="bg-section-label"><span class="bg-num">2</span> Time Period</div>
    <div class="bg-period-btns">
      <button class="bg-period-btn active" onclick="bgSetPeriod(this, 0)">All coverage</button>
      <button class="bg-period-btn" onclick="bgSetPeriod(this, 30)">Last month</button>
      <button class="bg-period-btn" onclick="bgSetPeriod(this, 7)">Last week</button>
      <button class="bg-period-btn" onclick="bgSetPeriod(this, 1)">Last 24h</button>
    </div>
    <div class="bg-article-preview" id="bg-article-preview">Loading…</div>
  </div>

  <hr class="bg-divider">

  <!-- 3. BRIEF TYPE -->
  <div class="bg-section">
    <div class="bg-section-label"><span class="bg-num">3</span> Brief Type</div>
    <div class="bg-type-cards">
      <div class="bg-type-card" id="bg-type-short" onclick="bgSetType(\'short\')">
        <div class="bg-type-card-icon">⚡</div>
        <div class="bg-type-card-name">Short Brief</div>
        <div class="bg-type-card-meta">~60s · concise overview</div>
        <div class="bg-type-check">✓</div>
      </div>
      <div class="bg-type-card active" id="bg-type-full" onclick="bgSetType(\'full\')">
        <div class="bg-type-card-icon">✦</div>
        <div class="bg-type-card-name">Full Intelligence Brief</div>
        <div class="bg-type-card-meta">~90s · with charts & analysis</div>
        <div class="bg-type-check">✓</div>
      </div>
    </div>
  </div>

  <hr class="bg-divider">

  <!-- Generate -->
  <button class="bg-generate-btn" id="bg-generate-btn" onclick="bgGenerate()">✦ Generate Brief</button>
</div>

'''

if OLD_HTML_ANCHOR in src:
    src = src.replace(OLD_HTML_ANCHOR, BRIEFING_HTML + OLD_HTML_ANCHOR)
    results.append("Patch 3 (HTML): OK")
else:
    results.append("Patch 3 (HTML): FAILED")

# ── Patch 4: Add briefing tab handling to switchMode ────────────────────────
OLD_SWITCH = '''  if (mode === 'themes') {
    newsfeedEl.classList.add('inactive');
    themesEl.classList.add('active');
    ktView.classList.add('visible');
    if (mainLayout) mainLayout.style.display = 'none';
    if (feedHeader) feedHeader.style.display = 'none';
    if (tallyBar)   tallyBar.style.display = 'none';
    if (actBar)     actBar.style.display = 'none';
    if (mobileFilter) mobileFilter.style.display = 'none';
    mainNav.style.display = 'none';
    renderKeyThemes();
  } else {
    newsfeedEl.classList.remove('inactive');
    themesEl.classList.remove('active');
    ktView.classList.remove('visible');
    if (mainLayout) mainLayout.style.display = '';
    if (feedHeader) feedHeader.style.display = '';
    if (tallyBar)   tallyBar.style.display = '';
    if (actBar)     actBar.style.display = '';
    mainNav.style.display = '';
  }'''

NEW_SWITCH = '''  const briefingEl  = document.getElementById('tab-briefing');
  const briefingView = document.getElementById('briefing-view');

  // Reset all tabs to inactive state
  newsfeedEl.classList.remove('inactive');
  themesEl.classList.remove('active');
  if (briefingEl) briefingEl.classList.remove('active');

  if (mode === 'themes') {
    newsfeedEl.classList.add('inactive');
    themesEl.classList.add('active');
    ktView.classList.add('visible');
    if (briefingView) briefingView.classList.remove('visible');
    if (mainLayout) mainLayout.style.display = 'none';
    if (feedHeader) feedHeader.style.display = 'none';
    if (tallyBar)   tallyBar.style.display = 'none';
    if (actBar)     actBar.style.display = 'none';
    if (mobileFilter) mobileFilter.style.display = 'none';
    mainNav.style.display = 'none';
    renderKeyThemes();
  } else if (mode === 'briefing') {
    newsfeedEl.classList.add('inactive');
    if (briefingEl) briefingEl.classList.add('active');
    ktView.classList.remove('visible');
    if (briefingView) briefingView.classList.add('visible');
    if (mainLayout) mainLayout.style.display = 'none';
    if (feedHeader) feedHeader.style.display = 'none';
    if (tallyBar)   tallyBar.style.display = 'none';
    if (actBar)     actBar.style.display = 'none';
    if (mobileFilter) mobileFilter.style.display = 'none';
    mainNav.style.display = 'none';
    bgInit();
  } else {
    ktView.classList.remove('visible');
    if (briefingView) briefingView.classList.remove('visible');
    if (mainLayout) mainLayout.style.display = '';
    if (feedHeader) feedHeader.style.display = '';
    if (tallyBar)   tallyBar.style.display = '';
    if (actBar)     actBar.style.display = '';
    mainNav.style.display = '';
  }'''

if OLD_SWITCH in src:
    src = src.replace(OLD_SWITCH, NEW_SWITCH)
    results.append("Patch 4 (switchMode): OK")
else:
    results.append("Patch 4 (switchMode): FAILED")

# ── Patch 5: Add briefing JS before generateThemes function ─────────────────
OLD_JS_ANCHOR = 'async function generateThemes(forceReseed = false) {'

BRIEFING_JS = '''// ── Briefing Generator ────────────────────────────────────────────────────
let bgPeriodDays = 0;   // 0 = all time
let bgBriefType = 'full';

function bgInit() {
  // Populate theme dropdown
  const sel = document.getElementById('bg-theme-select');
  if (sel && ktThemes && ktThemes.length) {
    sel.innerHTML = '<option value="">— choose a theme —</option>' +
      ktThemes.map((t,i) => `<option value="${i}">${t.emoji || ''} ${t.name}</option>`).join('');
  }
  bgUpdatePreview();
}

function bgUpdateTopic() {
  const mode = document.querySelector('input[name="bg-topic"]:checked').value;
  const themeSelect = document.getElementById('bg-theme-select');
  const focusedInput = document.getElementById('bg-focused-input');
  themeSelect.style.display = mode === 'theme' ? 'block' : 'none';
  focusedInput.style.display = mode === 'focused' ? 'flex' : 'none';
  bgUpdatePreview();
}

function bgSetPeriod(btn, days) {
  document.querySelectorAll('.bg-period-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  bgPeriodDays = days;
  bgUpdatePreview();
}

function bgSetType(type) {
  bgBriefType = type;
  document.getElementById('bg-type-short').classList.toggle('active', type === 'short');
  document.getElementById('bg-type-full').classList.toggle('active', type === 'full');
}

function bgGetFilteredArticles() {
  const mode = document.querySelector('input[name="bg-topic"]:checked').value;
  let pool = articles || [];

  // Time filter
  if (bgPeriodDays > 0) {
    const cutoff = Date.now() - bgPeriodDays * 24 * 60 * 60 * 1000;
    pool = pool.filter(a => {
      if (a.pub_date) {
        const d = new Date(a.pub_date).getTime();
        if (!isNaN(d)) return d >= cutoff;
      }
      return (a.saved_at || 0) >= cutoff;
    });
  }

  // Topic filter
  if (mode === 'theme') {
    const idx = parseInt(document.getElementById('bg-theme-select').value);
    if (!isNaN(idx) && ktThemes && ktThemes[idx]) {
      pool = getThemeArticles(ktThemes[idx]).filter(a =>
        bgPeriodDays === 0 || pool.some(p => p.id === a.id)
      );
    }
  } else if (mode === 'focused') {
    const topic = (document.getElementById('bg-focused-text').value || '').trim().toLowerCase();
    if (topic) {
      const words = topic.split(/\s+/).filter(w => w.length > 3);
      pool = pool.filter(a => {
        const text = ((a.title||'') + ' ' + (a.summary||'')).toLowerCase();
        return words.some(w => text.includes(w));
      });
    }
  }

  return pool.filter(a => a.summary); // only articles with summaries
}

function bgUpdatePreview() {
  const preview = document.getElementById('bg-article-preview');
  if (!preview) return;
  const filtered = bgGetFilteredArticles();
  if (!filtered.length) {
    preview.textContent = 'No articles match this selection.';
    document.getElementById('bg-generate-btn').disabled = true;
    return;
  }
  document.getElementById('bg-generate-btn').disabled = false;
  const sources = {};
  filtered.forEach(a => { sources[a.source] = (sources[a.source]||0)+1; });
  const topSources = Object.entries(sources).sort((a,b)=>b[1]-a[1]).slice(0,4)
    .map(([s,n]) => `${s} (${n})`).join(', ');
  preview.textContent = `Drawing from ${filtered.length} articles — ${topSources}${filtered.length > 4 ? ' and more' : ''}`;
}

async function bgGenerate() {
  const mode = document.querySelector('input[name="bg-topic"]:checked').value;
  const filteredArts = bgGetFilteredArticles();

  if (!filteredArts.length) { toast('No articles match this selection'); return; }

  if (mode === 'theme') {
    // Use existing downloadBriefPDF pipeline for theme briefs
    const idx = parseInt(document.getElementById('bg-theme-select').value);
    if (isNaN(idx) || !ktThemes || !ktThemes[idx]) { toast('Please select a theme'); return; }
    // Switch to themes view temporarily to get the theme index right
    await downloadBriefPDF(idx, bgBriefType);
    return;
  }

  // For "all themes" and "focused" — use the AI Analysis pipeline with enhanced prompt
  const guidance = (document.getElementById('bg-guidance-text') && mode === 'focused')
    ? (document.getElementById('bg-guidance-text').value || '').trim() : '';
  const focusedTopic = mode === 'focused'
    ? (document.getElementById('bg-focused-text').value || '').trim() : '';

  const modal = document.getElementById('kt-brief-modal');
  const content = document.getElementById('kt-brief-modal-content');
  if (!modal || !content) return;

  modal.classList.add('open');

  const steps = bgBriefType === 'short'
    ? ['Reading articles…', 'Analysing key developments…', 'Drafting brief…']
    : ['Reading articles…', 'Identifying key developments…', 'Analysing implications…', 'Drafting strategic brief…', 'Finalising…'];

  let stepIdx = 0, secs = 0;
  content.innerHTML = `
    <div style="padding:40px 24px;text-align:center">
      <div style="font-size:32px;margin-bottom:16px">⏳</div>
      <div style="font-family:\'Playfair Display\',serif;font-size:17px;margin-bottom:8px" id="bg-step-msg">${steps[0]}</div>
      <div style="font-size:11px;color:var(--ink-3)" id="bg-secs">0s elapsed</div>
      <div style="width:300px;height:4px;background:#e8e0d4;border-radius:2px;overflow:hidden;margin:16px auto 0">
        <div id="bg-prog-bar" style="height:100%;width:5%;background:var(--accent);border-radius:2px;transition:width 2s"></div>
      </div>
    </div>`;

  const stepTimer = setInterval(() => {
    secs++;
    const secEl = document.getElementById('bg-secs');
    if (secEl) secEl.textContent = secs + 's elapsed';
    if (secs % 12 === 0 && stepIdx < steps.length - 1) {
      stepIdx++;
      const msgEl = document.getElementById('bg-step-msg');
      if (msgEl) msgEl.textContent = steps[stepIdx];
    }
    const prog = Math.min(5 + secs * 1.2, 90);
    const bar = document.getElementById('bg-prog-bar');
    if (bar) bar.style.width = prog + '%';
  }, 1000);

  try {
    // Build context from filtered articles
    const maxArts = bgBriefType === 'short' ? 40 : 80;
    const contextArts = filteredArts.slice(0, maxArts);
    const context = contextArts.map(a =>
      `[${a.source}${a.pub_date ? ', ' + a.pub_date : ''}] ${a.title}: ${(a.summary||'').slice(0,300)}`
    ).join('\n');

    const periodLabel = bgPeriodDays === 0 ? 'all available coverage'
      : bgPeriodDays === 1 ? 'last 24 hours'
      : bgPeriodDays === 7 ? 'last 7 days' : 'last 30 days';

    let userMsg = `Articles (${contextArts.length}, ${periodLabel}):\n${context}`;
    if (focusedTopic) userMsg += `\n\nFocus: ${focusedTopic}`;
    if (guidance) userMsg += `\n\nGuidance: ${guidance}`;

    const maxTokens = bgBriefType === 'short' ? 1500 : 4000;
    const system = `You are an intelligence analyst producing a ${bgBriefType === 'short' ? 'concise' : 'comprehensive'} strategic intelligence brief.
Structure your response with these sections:
## Executive Summary
(2-3 sentences — the single most important insight)
## Key Developments
(4-6 themes as ### subheadings, each with 3-4 bullet points citing [Source, Date])
## Strategic Implications
(3 bullet points on what this means going forward)
${bgBriefType === 'full' ? '## Watch List\n(2-3 items to monitor in coming days)\n' : ''}
Always cite sources. Prioritise recent articles. ${guidance ? 'Incorporate this guidance: ' + guidance : ''}`;

    const resp = await fetch(SERVER + '/api/claude', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        max_tokens: maxTokens,
        system,
        messages: [{role: 'user', content: userMsg}]
      })
    });
    const data = await resp.json();
    const briefText = data.content && data.content[0] && data.content[0].text || '';

    clearInterval(stepTimer);
    const bar = document.getElementById('bg-prog-bar');
    if (bar) bar.style.width = '100%';

    // Render brief in modal
    let html = briefText
      .replace(/## Executive Summary/g, '<h2>Executive Summary</h2>')
      .replace(/## (.*)/g, '<h2>$1</h2>')
      .replace(/### (.*)/g, '<h3>$1</h3>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/^[-•] (.+)$/gm, '<li>$1</li>')
      .replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>')
      .replace(/<\/ul>\s*<ul>/g, '')
      .replace(/\n\n/g, '</p><p>')
      .replace(/^(?!<[hul])/gm, '');

    html = html.replace(
      /<h2>Executive Summary<\/h2>([\s\S]*?)(?=<h2>|$)/,
      (m, body) => `<h2>Executive Summary</h2><div class="kt-brief-exec">${body.trim()}</div>`
    );

    const periodStr = bgPeriodDays === 0 ? 'All coverage' : bgPeriodDays === 1 ? 'Last 24h' : bgPeriodDays === 7 ? 'Last 7 days' : 'Last 30 days';
    const topicStr = mode === 'focused' && focusedTopic ? focusedTopic : mode === 'all' ? 'All themes' : (ktThemes && ktThemes[parseInt(document.getElementById('bg-theme-select').value)] || {name:''}).name;

    content.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:flex-start;padding:20px 24px 0">
        <div>
          <div style="font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:var(--accent);font-weight:500;margin-bottom:4px">${bgBriefType === 'short' ? 'Short Brief' : 'Full Intelligence Brief'} · ${periodStr}</div>
          <div style="font-family:\'Playfair Display\',serif;font-size:20px;font-weight:700">${topicStr || 'Intelligence Brief'}</div>
          <div style="font-size:11px;color:var(--ink-3);margin-top:2px">${filteredArts.length} articles · ${new Date().toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric'})}</div>
        </div>
        <button onclick="document.getElementById('kt-brief-modal').classList.remove('open')"
          style="background:none;border:none;font-size:22px;cursor:pointer;color:var(--ink-3);line-height:1;padding:0">×</button>
      </div>
      <div class="kt-brief-content" style="padding:16px 24px 24px"><p>${html}</p></div>`;

  } catch(e) {
    clearInterval(stepTimer);
    toast('Brief failed: ' + e.message);
    modal.classList.remove('open');
  }
}

'''

if OLD_JS_ANCHOR in src:
    src = src.replace(OLD_JS_ANCHOR, BRIEFING_JS + OLD_JS_ANCHOR)
    results.append("Patch 5 (JS): OK")
else:
    results.append("Patch 5 (JS): FAILED")

with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(src)

for r in results:
    print(r)
