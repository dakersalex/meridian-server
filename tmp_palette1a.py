
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# ── 1. Fix logo gap — remove space between text node and span
old_logo = '<div class="logo">Meri<span>dian</span></div>'
new_logo = '<div class="logo">Meri<span>dian</span></div>'
# The real fix is in the CSS — letter-spacing on .logo was fine,
# but Playfair Display renders a gap when span starts a new text node.
# Fix by making the accent colour inline with no whitespace.
# Current HTML is already correct, gap is actually from CSS font rendering.
# Real fix: add font-variant or adjust letter-spacing on the span.

old_logo_css = ".logo { font-family: 'Playfair Display', serif; font-size: 26px; font-weight: 600; letter-spacing: -0.5px; }"
new_logo_css = ".logo { font-family: 'Playfair Display', serif; font-size: 26px; font-weight: 600; letter-spacing: -0.5px; word-spacing: -2px; }\n.logo span { letter-spacing: -0.5px; }"
if old_logo_css in html:
    html = html.replace(old_logo_css, new_logo_css)
    results.append('Logo gap fix: OK')
else:
    results.append('Logo gap: NOT FOUND')

# ── 2. Remove duplicate "connected" from folder-switcher nav row
# The folder-switcher currently shows server status — remove it entirely
# (masthead already shows it)
old_fs_status = '''    <div class="server-status">
      <div class="status-dot" id="status-dot"></div>
      <span id="status-text" style="font-size:11px;color:var(--ink-3)">Checking server…</span>
    </div>
    <span class="last-sync" id="last-sync-label" style="display:none"></span>
    <button class="btn btn-dark" onclick="openAIPanel()" style="background:var(--accent);font-size:11px;padding:5px 14px">✦ AI Analysis</button>'''
new_fs_status = '''    <button class="btn btn-dark" onclick="openAIPanel()" style="background:var(--accent);font-size:11px;padding:5px 14px">✦ AI Analysis</button>
    <span class="last-sync" id="last-sync-label" style="display:none"></span>'''
if old_fs_status in html:
    html = html.replace(old_fs_status, new_fs_status)
    results.append('Duplicate connected removed: OK')
else:
    results.append('Duplicate connected: NOT FOUND')

# ── 3. Add green/red dot to masthead status line
# Masthead currently has: last-sync-masthead span + status-dot + status-text
# Add the dot inline before the text
old_mast_status = '''    <div style="display:flex;align-items:center;gap:6px">
      <span id="last-sync-masthead" style="font-size:11px;color:var(--ink-3)"></span>
      <div class="server-status" style="font-size:11px">
        <div class="status-dot" id="status-dot"></div>
        <span id="status-text" style="font-size:11px;color:var(--ink-3)">Checking…</span>
      </div>
    </div>'''
new_mast_status = '''    <div style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--ink-3)">
      <span id="last-sync-masthead"></span>
      <div class="status-dot" id="status-dot"></div>
      <span id="status-text">Checking…</span>
    </div>'''
if old_mast_status in html:
    html = html.replace(old_mast_status, new_mast_status)
    results.append('Masthead status dot: OK')
else:
    results.append('Masthead status: NOT FOUND')

# ── 4. AI Analysis button — amber accent (already correct, ensure it stays)
# ── 5. Sync all button — muted amber fill, no border
# Current sync btn: background:var(--accent)
# Change to: background: #d98a4e (midpoint between #c4783a accent and #faf8f4 paper)
# No border — just a softer amber fill with white text
old_sync = 'onclick="syncAll()" id="sync-all-btn" style="font-size:10px;padding:3px 9px;background:var(--accent)"'
new_sync = 'onclick="syncAll()" id="sync-all-btn" style="font-size:10px;padding:3px 9px;background:#d4976a;border:none;color:white;"'
if old_sync in html:
    html = html.replace(old_sync, new_sync)
    results.append('Sync btn muted amber: OK')
else:
    results.append('Sync btn: NOT FOUND')

# ── 6. Card background white, headers warm cream
# paper is already #faf8f4 — add --card: #ffffff variable
# Change feed-area background
old_feed_area_css = '.feed-area { padding: 0 20px 20px; border-right: 1px solid var(--rule); }'
new_feed_area_css = '.feed-area { padding: 0 20px 20px; border-right: 1px solid var(--rule); background: #ffffff; }'
if old_feed_area_css in html:
    html = html.replace(old_feed_area_css, new_feed_area_css)
    results.append('Feed area white: OK')
else:
    results.append('Feed area: NOT FOUND')

# ── 7. Filter dropdowns — white bg, bolder outline
old_filter_sel = '.filter-select { font-size: 11px; padding: 3px 8px; border: 1px solid var(--rule); background: var(--paper); color: var(--ink-2); font-family: \'IBM Plex Sans\', sans-serif; cursor: pointer; }'
new_filter_sel = '.filter-select { font-size: 11px; padding: 3px 8px; border: 1px solid rgba(0,0,0,0.25); background: #ffffff; color: var(--ink-2); font-family: \'IBM Plex Sans\', sans-serif; cursor: pointer; font-weight: 500; }'
if old_filter_sel in html:
    html = html.replace(old_filter_sel, new_filter_sel)
    results.append('Filter selects: OK')
else:
    results.append('Filter selects: NOT FOUND')

# ── 8. Row 4 info strip — remove amber from AI picks count
# AI picks count is currently color:var(--accent) — change to ink
old_ai_count = '<strong style="color:var(--accent);font-weight:600"><span id="tally-ai">–</span></strong>'
new_ai_count = '<strong style="color:var(--ink);font-weight:600"><span id="tally-ai">–</span></strong>'
if old_ai_count in html:
    html = html.replace(old_ai_count, new_ai_count)
    results.append('AI picks ink colour: OK')
else:
    results.append('AI picks count: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
