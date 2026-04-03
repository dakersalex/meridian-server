
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# ── 1. Folder-switcher: add Sync all + Clip + Stats chip, move buttons here
old_fs = '''<div id="folder-switcher">
  <button class="folder-tab folder-tab-newsfeed active" id="tab-newsfeed" onclick="switchMode('newsfeed')"><span class="nav-dot"></span>News Feed</button>
  <button class="folder-tab folder-tab-themes" id="tab-themes" onclick="switchMode('themes')"><span class="nav-dot"></span>Key Themes</button>
  <button class="folder-tab folder-tab-briefing" id="tab-briefing" onclick="switchMode('briefing')"><span class="nav-dot"></span>Briefing Generator</button>
  <div style="margin-left:auto;display:flex;align-items:center;gap:12px">
    <span class="last-sync" id="last-sync-label" style="display:none"></span>
    <button class="btn btn-dark" onclick="openAIPanel()" style="background:var(--accent);font-size:11px;padding:5px 14px">✦ AI Analysis</button>
    <button class="btn btn-dark mobile-sync-btn" onclick="syncAll()" style="display:none;background:var(--accent);font-size:11px;padding:4px 10px">🔄 Sync</button>
  </div>
</div>'''

new_fs = '''<div id="folder-switcher">
  <button class="folder-tab folder-tab-newsfeed active" id="tab-newsfeed" onclick="switchMode('newsfeed')"><span class="nav-dot"></span>News Feed</button>
  <button class="folder-tab folder-tab-themes" id="tab-themes" onclick="switchMode('themes')"><span class="nav-dot"></span>Key Themes</button>
  <button class="folder-tab folder-tab-briefing" id="tab-briefing" onclick="switchMode('briefing')"><span class="nav-dot"></span>Briefing Generator</button>
  <div style="margin-left:auto;display:flex;align-items:center;gap:8px">
    <span class="last-sync" id="last-sync-label" style="display:none"></span>
    <button id="stats-toggle-btn" onclick="toggleStatsStrip()" style="font-size:11px;padding:4px 10px;background:transparent;border:1px solid rgba(0,0,0,0.2);color:var(--ink-2);border-radius:4px;cursor:pointer;font-family:inherit;display:flex;align-items:center;gap:5px;">📊 Stats</button>
    <button class="btn btn-outline" onclick="clipBloomberg()" id="clip-bbg-btn" style="font-size:10px;padding:3px 7px;display:none">📎 Clip Bloomberg</button>
    <button class="btn btn-dark" onclick="syncAll()" id="sync-all-btn" style="font-size:10px;padding:4px 10px;background:#d4976a;border:none;color:white;">🔄 Sync all</button>
    <button class="btn btn-dark" onclick="openAIPanel()" style="background:var(--accent);font-size:11px;padding:5px 14px">✦ AI Analysis</button>
  </div>
</div>'''

if old_fs in html:
    html = html.replace(old_fs, new_fs)
    results.append('folder-switcher: OK')
else:
    results.append('folder-switcher: NOT FOUND')

# ── 2. Info-strip: hide by default, change bg to var(--paper), remove sync buttons from it
old_strip = '''<div id="info-strip" style="display:flex;align-items:center;gap:10px;padding:6px 20px;background:var(--paper-2);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap;position:sticky;top:147px;z-index:52;isolation:isolate;">
  <span style="color:var(--ink-2);white-space:nowrap">My saves: <strong style="color:var(--ink);font-weight:600"><span id="tally-saves">–</span></strong> <span id="tally-saves-pct" style="color:var(--ink-3)"></span></span>
  <div style="width:1px;height:12px;background:var(--rule);flex-shrink:0"></div>
  <span style="color:var(--ink-2);white-space:nowrap">AI picks: <strong style="color:var(--ink);font-weight:600"><span id="tally-ai">–</span></strong> <span id="tally-ai-pct" style="color:var(--ink-3)"></span></span>
  <div style="width:1px;height:12px;background:var(--rule);flex-shrink:0"></div>
  <span style="font-weight:500;color:var(--ink-2);white-space:nowrap">24h:</span>
  <span id="act-ft-pill" class="activity-pill activity-pill-zero"><span style="color:#0d4a8a;font-weight:500">FT</span> <span id="act-ft">–</span></span>
  <span id="act-eco-pill" class="activity-pill activity-pill-zero"><span style="color:#8b1a1a;font-weight:500">Economist</span> <span id="act-eco">–</span></span>
  <span id="act-fa-pill" class="activity-pill activity-pill-zero"><span style="color:#1e4d8c;font-weight:500">FA</span> <span id="act-fa">–</span></span>
  <span id="act-bbg-pill" class="activity-pill activity-pill-zero"><span style="color:#555;font-weight:500">Bloomberg</span> <span id="act-bbg">–</span></span>
  <span id="act-fp-pill" class="activity-pill activity-pill-zero"><span style="color:#2d6b45;font-weight:500">Foreign Policy</span> <span id="act-fp">–</span></span>
  <span class="activity-warning" id="act-warning" style="display:none">⚠ FT sync found 0 articles</span>
  <span style="display:none" id="tally-total">0</span>
  <div style="margin-left:auto;display:flex;gap:6px;flex-shrink:0">
    <button class="btn btn-dark" onclick="syncAll()" id="sync-all-btn" style="font-size:10px;padding:3px 9px;background:#d4976a;border:none;color:white;">🔄 Sync all</button>
    <button class="btn btn-outline" onclick="clipBloomberg()" id="clip-bbg-btn" style="font-size:10px;padding:3px 7px;display:none">📎 Clip Bloomberg</button>
  </div>
</div>'''

new_strip = '''<div id="info-strip" style="display:none;align-items:center;gap:10px;padding:6px 20px;background:var(--paper);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap;position:sticky;top:147px;z-index:52;isolation:isolate;">
  <span style="color:var(--ink-2);white-space:nowrap">My saves: <strong style="color:var(--ink);font-weight:600"><span id="tally-saves">–</span></strong> <span id="tally-saves-pct" style="color:var(--ink-3)"></span></span>
  <div style="width:1px;height:12px;background:var(--rule);flex-shrink:0"></div>
  <span style="color:var(--ink-2);white-space:nowrap">AI picks: <strong style="color:var(--ink);font-weight:600"><span id="tally-ai">–</span></strong> <span id="tally-ai-pct" style="color:var(--ink-3)"></span></span>
  <div style="width:1px;height:12px;background:var(--rule);flex-shrink:0"></div>
  <span style="font-weight:500;color:var(--ink-2);white-space:nowrap">24h:</span>
  <span id="act-ft-pill" class="activity-pill activity-pill-zero"><span style="color:#0d4a8a;font-weight:500">FT</span> <span id="act-ft">–</span></span>
  <span id="act-eco-pill" class="activity-pill activity-pill-zero"><span style="color:#8b1a1a;font-weight:500">Economist</span> <span id="act-eco">–</span></span>
  <span id="act-fa-pill" class="activity-pill activity-pill-zero"><span style="color:#1e4d8c;font-weight:500">FA</span> <span id="act-fa">–</span></span>
  <span id="act-bbg-pill" class="activity-pill activity-pill-zero"><span style="color:#555;font-weight:500">Bloomberg</span> <span id="act-bbg">–</span></span>
  <span id="act-fp-pill" class="activity-pill activity-pill-zero"><span style="color:#2d6b45;font-weight:500">Foreign Policy</span> <span id="act-fp">–</span></span>
  <span class="activity-warning" id="act-warning" style="display:none">⚠ FT sync found 0 articles</span>
  <span style="display:none" id="tally-total">0</span>
</div>'''

if old_strip in html:
    html = html.replace(old_strip, new_strip)
    results.append('info-strip hidden+paper: OK')
else:
    results.append('info-strip: NOT FOUND')

# ── 3. Add toggleStatsStrip() JS function
# Insert just before the closing recalcStickyTops definition
old_fn = 'function recalcStickyTops() {'
new_fn = '''function toggleStatsStrip() {
  const strip = document.getElementById('info-strip');
  const btn = document.getElementById('stats-toggle-btn');
  const isVisible = strip.style.display === 'flex';
  strip.style.display = isVisible ? 'none' : 'flex';
  btn.style.background = isVisible ? 'transparent' : 'var(--paper-3)';
  btn.style.color = isVisible ? 'var(--ink-2)' : 'var(--ink)';
  recalcStickyTops();
}
function recalcStickyTops() {'''

if old_fn in html:
    html = html.replace(old_fn, new_fn, 1)
    results.append('toggleStatsStrip: OK')
else:
    results.append('toggleStatsStrip: NOT FOUND')

# ── 4. Fix switchMode() to handle info-strip display:none default
# switchMode restores info-strip to display:flex — change to only restore if stats are open
old_switchmode_is = "document.getElementById('info-strip').style.display='flex';"
new_switchmode_is = "if(document.getElementById('stats-toggle-btn').style.background!=='transparent')document.getElementById('info-strip').style.display='flex';"
if old_switchmode_is in html:
    html = html.replace(old_switchmode_is, new_switchmode_is)
    results.append('switchMode info-strip guard: OK')
else:
    results.append('switchMode guard: NOT FOUND (may be fine)')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
