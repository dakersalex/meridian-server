
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# ─────────────────────────────────────────────
# 1. REPLACE folder-switcher CSS
# ─────────────────────────────────────────────
old_css_folder = '''#folder-switcher {
  background: var(--paper-2);
  padding: 8px 20px 0;
  display: flex;
  align-items: flex-end;
  border-bottom: 2.5px solid var(--ink);
  position: relative;
  z-index: 10;
}
.folder-tab {
  height: 30px;
  padding: 0 20px;
  font-size: 12px;
  font-weight: 500;
  font-family: 'IBM Plex Sans', sans-serif;
  border: 1.5px solid var(--ink);
  border-bottom: none;
  border-radius: 5px 5px 0 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  letter-spacing: 0.3px;
  margin-bottom: -2.5px;
  transition: filter 0.15s;
}
.folder-tab-newsfeed {
  background: var(--accent);
  color: var(--paper);
  height: 34px;
  z-index: 3;
  position: relative;
  border-bottom: 2.5px solid var(--accent);
  box-shadow: -2px -3px 5px rgba(0,0,0,0.18), 2px -3px 5px rgba(0,0,0,0.10);
}
.folder-tab-themes {
  background: var(--paper-3);
  color: var(--ink-3);
  height: 28px;
  z-index: 1;
  position: relative;
  margin-left: 2px;
  border-bottom: none;
  box-shadow: 1px -2px 3px rgba(0,0,0,0.08);
}
.folder-tab-themes.active {
  background: var(--accent);
  color: var(--paper);
  height: 34px;
  z-index: 3;
  border-bottom: 2.5px solid var(--accent);
  box-shadow: -2px -3px 5px rgba(0,0,0,0.18), 2px -3px 5px rgba(0,0,0,0.10);
}

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
}'''

new_css_folder = '''/* ── 2D nav: dot + background on active ── */
#folder-switcher {
  background: var(--paper);
  padding: 8px 20px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--rule);
  gap: 2px;
  z-index: 10;
  position: relative;
}
#folder-switcher-logo {
  font-size: 15px;
  font-weight: 500;
  letter-spacing: -0.3px;
  color: var(--accent);
  padding-right: 20px;
  margin-right: 6px;
  border-right: 1px solid var(--rule);
  line-height: 1;
}
#folder-switcher-logo span { color: var(--ink); }
.folder-tab {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px 14px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  font-family: 'IBM Plex Sans', sans-serif;
  border: none;
  background: none;
  color: var(--ink-3);
  cursor: pointer;
  letter-spacing: 0.2px;
  transition: background 0.12s, color 0.12s;
  white-space: nowrap;
}
.folder-tab:hover { background: var(--paper-2); color: var(--ink); }
.folder-tab .nav-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--rule); flex-shrink: 0;
  transition: background 0.12s;
}
.folder-tab.active {
  background: var(--paper-2);
  color: var(--ink);
}
.folder-tab.active .nav-dot { background: var(--accent); }
.folder-tab-newsfeed {}
.folder-tab-themes {}
.folder-tab-briefing {}'''

if old_css_folder in html:
    html = html.replace(old_css_folder, new_css_folder)
    results.append('CSS folder tabs: OK')
else:
    results.append('CSS folder tabs: NOT FOUND')

# ─────────────────────────────────────────────
# 2. REPLACE folder-switcher HTML + server-bar
#    Merge into: folder-switcher (logo + 3 nav items + server status + sync time + AI Analysis)
#    Then: tally-bar and activity-bar merged into one info strip
# ─────────────────────────────────────────────
old_html_top = '''<div id="folder-switcher">
  <button class="folder-tab folder-tab-newsfeed" id="tab-newsfeed" onclick="switchMode('newsfeed')">News Feed</button>
  <button class="folder-tab folder-tab-themes" id="tab-themes" onclick="switchMode('themes')">Key Themes</button>
  <button class="folder-tab folder-tab-briefing" id="tab-briefing" onclick="switchMode('briefing')">Briefing Generator</button>
  <div class="folder-spacer"></div>
</div>
<div class="server-bar">
  <div class="server-status">
    <div class="status-dot" id="status-dot"></div>
    <span id="status-text">Checking server…</span>
  </div>
  <div class="sync-sources">

    <span class="last-sync" id="last-sync-label"></span><button class="btn btn-dark" onclick="openAIPanel()" style="margin-left:auto;background:var(--accent);font-size:12px;padding:5px 14px">✦ AI Analysis</button>
    <button class="btn btn-dark mobile-sync-btn" onclick="syncAll()" style="display:none;background:var(--accent);font-size:11px;padding:4px 10px;margin-left:6px">🔄 Sync</button>
  </div>

</div>'''

new_html_top = '''<div id="folder-switcher">
  <div id="folder-switcher-logo">Meri<span>dian</span></div>
  <button class="folder-tab folder-tab-newsfeed active" id="tab-newsfeed" onclick="switchMode('newsfeed')"><span class="nav-dot"></span>News Feed</button>
  <button class="folder-tab folder-tab-themes" id="tab-themes" onclick="switchMode('themes')"><span class="nav-dot"></span>Key Themes</button>
  <button class="folder-tab folder-tab-briefing" id="tab-briefing" onclick="switchMode('briefing')"><span class="nav-dot"></span>Briefing Generator</button>
  <div style="margin-left:auto;display:flex;align-items:center;gap:12px">
    <div class="server-status">
      <div class="status-dot" id="status-dot"></div>
      <span id="status-text" style="font-size:11px;color:var(--ink-3)">Checking server…</span>
    </div>
    <span class="last-sync" id="last-sync-label" style="font-size:11px;color:var(--ink-3)"></span>
    <button class="btn btn-dark" onclick="openAIPanel()" style="background:var(--accent);font-size:11px;padding:5px 14px">✦ AI Analysis</button>
    <button class="btn btn-dark mobile-sync-btn" onclick="syncAll()" style="display:none;background:var(--accent);font-size:11px;padding:4px 10px">🔄 Sync</button>
  </div>
</div>'''

if old_html_top in html:
    html = html.replace(old_html_top, new_html_top)
    results.append('HTML top bar: OK')
else:
    results.append('HTML top bar: NOT FOUND')

# ─────────────────────────────────────────────
# 3. REPLACE tally-bar + activity-bar with merged Option D info strip
# ─────────────────────────────────────────────
old_tally_activity = '''<div id="tally-bar" style="display:flex;align-items:center;gap:10px;padding:5px 20px;background:var(--paper-2);border-bottom:1px solid var(--rule);font-size:11px;color:var(--ink-3)">
  <span style="font-weight:500;color:var(--ink-2)">My saves:</span>
  <span style="font-weight:600;color:var(--ink)"><span id="tally-saves">–</span> <span id="tally-saves-pct" style="font-weight:400;color:var(--ink-3)"></span></span>
  <span style="color:var(--rule)">·</span>
  <span style="font-weight:500;color:var(--ink-2)">AI picks:</span>
  <span style="font-weight:600;color:var(--accent)"><span id="tally-ai">–</span> <span id="tally-ai-pct" style="font-weight:400;color:var(--ink-3)"></span></span>
  <span style="display:none" id="tally-total">0</span>
</div>
<div class="activity-bar" id="activity-bar" style="display:flex;align-items:center;gap:12px;padding:7px 20px;background:var(--paper-2);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:wrap">
  <span class="activity-label">Last 24h:</span>
  <span class="activity-source"><span style="color:#0d4a8a;font-weight:500">FT</span> <span class="activity-new" id="act-ft">+0</span></span>
  <span class="activity-source"><span style="color:#8b1a1a;font-weight:500">Economist</span> <span class="activity-new" id="act-eco">+0</span></span>
  <span class="activity-source"><span style="color:#1e4d8c;font-weight:500">FA</span> <span class="activity-new" id="act-fa">+0</span></span>
  <span class="activity-source"><span style="color:#555;font-weight:500">Bloomberg</span> <span class="activity-new" id="act-bbg">+0</span></span>
  <span class="activity-source"><span style="color:#2d6b45;font-weight:500">FP</span> <span class="activity-new" id="act-fp">+0</span></span>
  <span class="activity-warning" id="act-warning" style="display:none">⚠ FT sync found 0 articles</span>
  <span class="activity-sync-time" id="act-sync-time"></span>
  <div style="margin-left:auto;display:flex;gap:4px">
    <button class="btn btn-dark" onclick="syncAll()" id="sync-all-btn" style="font-size:10px;padding:3px 9px;background:var(--accent)">🔄 Sync all</button>
    <button class="btn btn-outline" onclick="clipBloomberg()" id="clip-bbg-btn" style="font-size:10px;padding:3px 7px;display:none">📎 Clip Bloomberg</button>
  </div>
</div>'''

new_tally_activity = '''<div id="info-strip" style="display:flex;align-items:center;gap:10px;padding:6px 20px;background:var(--paper-2);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap">
  <span style="color:var(--ink-2);white-space:nowrap">My saves: <strong style="color:var(--ink);font-weight:600"><span id="tally-saves">–</span></strong> <span id="tally-saves-pct" style="color:var(--ink-3)"></span></span>
  <div style="width:1px;height:12px;background:var(--rule);flex-shrink:0"></div>
  <span style="color:var(--ink-2);white-space:nowrap">AI picks: <strong style="color:var(--accent);font-weight:600"><span id="tally-ai">–</span></strong> <span id="tally-ai-pct" style="color:var(--ink-3)"></span></span>
  <div style="width:1px;height:12px;background:var(--rule);flex-shrink:0"></div>
  <span style="font-weight:500;color:var(--ink-2);white-space:nowrap">24h:</span>
  <span id="act-ft-pill" class="activity-pill activity-pill-zero"><span style="color:#0d4a8a;font-weight:500">FT</span> <span id="act-ft">–</span></span>
  <span id="act-eco-pill" class="activity-pill activity-pill-zero"><span style="color:#8b1a1a;font-weight:500">Economist</span> <span id="act-eco">–</span></span>
  <span id="act-fa-pill" class="activity-pill activity-pill-zero"><span style="color:#1e4d8c;font-weight:500">FA</span> <span id="act-fa">–</span></span>
  <span id="act-bbg-pill" class="activity-pill activity-pill-zero"><span style="color:#555;font-weight:500">Bloomberg</span> <span id="act-bbg">–</span></span>
  <span id="act-fp-pill" class="activity-pill activity-pill-zero"><span style="color:#2d6b45;font-weight:500">FP</span> <span id="act-fp">–</span></span>
  <span class="activity-warning" id="act-warning" style="display:none">⚠ FT sync found 0 articles</span>
  <span style="display:none" id="tally-total">0</span>
  <div style="margin-left:auto;display:flex;gap:6px;flex-shrink:0">
    <button class="btn btn-dark" onclick="syncAll()" id="sync-all-btn" style="font-size:10px;padding:3px 9px;background:var(--accent)">🔄 Sync all</button>
    <button class="btn btn-outline" onclick="clipBloomberg()" id="clip-bbg-btn" style="font-size:10px;padding:3px 7px;display:none">📎 Clip Bloomberg</button>
  </div>
</div>'''

if old_tally_activity in html:
    html = html.replace(old_tally_activity, new_tally_activity)
    results.append('HTML info strip: OK')
else:
    results.append('HTML info strip: NOT FOUND')

# ─────────────────────────────────────────────
# 4. ADD pill CSS + update auto-saved card styling
# ─────────────────────────────────────────────
old_activity_css = '''.activity-label { font-weight: 500; color: var(--ink-2); margin-right: 4px; }
.activity-source { display: flex; align-items: center; gap: 6px; }
.activity-new { '''

new_activity_css = '''.activity-label { font-weight: 500; color: var(--ink-2); margin-right: 4px; }
.activity-source { display: flex; align-items: center; gap: 6px; }
/* Activity pills for info strip */
.activity-pill {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11px; padding: 2px 8px; border-radius: 20px;
  border: 1px solid var(--rule); white-space: nowrap; flex-shrink: 0;
}
.activity-pill-zero { background: var(--paper-2); color: var(--ink-3); }
.activity-pill-active { background: #f5ede4; color: var(--accent); border-color: #e8c9a8; }
/* My saves vs AI card distinction */
.article-card.ai-pick { background: var(--paper); border-left: 3px solid var(--accent); }
.featured-card.ai-pick { background: var(--paper); border-left: 3px solid var(--accent); }
.activity-new { '''

if old_activity_css in html:
    html = html.replace(old_activity_css, new_activity_css)
    results.append('CSS pills + card: OK')
else:
    results.append('CSS pills + card: NOT FOUND')

# ─────────────────────────────────────────────
# 5. UPDATE switchMode JS to use new active class pattern
# ─────────────────────────────────────────────
old_switch = "document.querySelectorAll('.folder-tab').forEach(t=>t.classList.remove('active'));"
if old_switch in html:
    results.append('switchMode already uses .active: OK')
else:
    # Try to find and patch the switchMode function
    results.append('switchMode: check manually')

# ─────────────────────────────────────────────
# 6. UPDATE activity pill JS — make pills turn amber when non-zero
# ─────────────────────────────────────────────
old_set_count = '''    function setCount(id, n) {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = n === 0 ? '0 new' : '+' + n;
      el.className = 'activity-new' + (n === 0 ? ' none' : '');
    }
    setCount('act-ft',  recent['Financial Times'] || 0);
    setCount('act-eco', recent['The Economist']   || 0);
    setCount('act-fa',  recent['Foreign Affairs'] || 0);
    setCount('act-bbg', recent['Bloomberg']       || 0);
    setCount('act-fp',  recent['Foreign Policy']  || 0);'''

new_set_count = '''    function setCount(id, n) {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = n === 0 ? '—' : '+' + n;
      // Update the pill container class too
      const pill = document.getElementById(id + '-pill');
      if (pill) {
        pill.className = n > 0 ? 'activity-pill activity-pill-active' : 'activity-pill activity-pill-zero';
      }
    }
    setCount('act-ft',  recent['Financial Times'] || 0);
    setCount('act-eco', recent['The Economist']   || 0);
    setCount('act-fa',  recent['Foreign Affairs'] || 0);
    setCount('act-bbg', recent['Bloomberg']       || 0);
    setCount('act-fp',  recent['Foreign Policy']  || 0);'''

if old_set_count in html:
    html = html.replace(old_set_count, new_set_count)
    results.append('JS pill setCount: OK')
else:
    results.append('JS pill setCount: NOT FOUND')

# ─────────────────────────────────────────────
# 7. UPDATE article card rendering — add ai-pick class for auto_saved
#    and clearer "My save" vs "AI pick" badge
# ─────────────────────────────────────────────
old_auto_pill = "const autoPill=a.auto_saved?'<span style=\"font-size:10px;padding:2px 7px;border-radius:10px;background:var(--accent);color:#fff;font-weight:600;margin-left:6px\">✦ Auto</span>':'';\n    const autoStyle=a.auto_saved?';background:var(--paper-2)':'';"

new_auto_pill = "const autoPill=a.auto_saved?'<span style=\"font-size:10px;padding:2px 7px;border-radius:10px;background:var(--accent);color:#fff;font-weight:500;letter-spacing:0.3px;margin-left:6px\">✦ AI pick</span>':'<span style=\"font-size:10px;padding:2px 7px;border-radius:10px;background:var(--paper-3);color:var(--ink-3);font-weight:500;letter-spacing:0.3px;margin-left:6px;border:1px solid var(--rule)\">My save</span>';\n    const autoStyle=a.auto_saved?'':'';"

if old_auto_pill in html:
    html = html.replace(old_auto_pill, new_auto_pill)
    results.append('JS auto pill badge: OK')
else:
    results.append('JS auto pill badge: NOT FOUND')

# Also add ai-pick class to card divs
old_featured = '`<div class="featured-card" style="position:relative;padding-top:20px${autoStyle}"'
new_featured = '`<div class="featured-card${a.auto_saved?\' ai-pick\':\'\'}" style="position:relative;padding-top:20px"'
if old_featured in html:
    html = html.replace(old_featured, new_featured)
    results.append('featured-card ai-pick class: OK')
else:
    results.append('featured-card ai-pick class: NOT FOUND')

old_artcard = '`<div class="article-card" style="position:relative;padding-top:20px${autoStyle}"'
new_artcard = '`<div class="article-card${a.auto_saved?\' ai-pick\':\'\'}" style="position:relative;padding-top:20px"'
if old_artcard in html:
    html = html.replace(old_artcard, new_artcard)
    results.append('article-card ai-pick class: OK')
else:
    results.append('article-card ai-pick class: NOT FOUND')

# ─────────────────────────────────────────────
# 8. FIX switchMode to use .active class (remove old per-class active logic)
# ─────────────────────────────────────────────
old_switcher_inactive = '''.folder-tab-newsfeed.inactive {'''
if old_switcher_inactive in html:
    # Find and check switchMode function
    results.append('inactive class exists: check switchMode')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
