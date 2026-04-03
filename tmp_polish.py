
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# ── 1. Remove status-dot-nav from main-nav (the duplicate server status in row 3)
old_nav_status = '''  <div style="margin-left:auto;display:flex;align-items:center;gap:10px;padding-right:4px">
    <div style="display:flex;align-items:center;gap:5px;font-size:11px;color:var(--ink-3)">
      <div class="status-dot" id="status-dot-nav"></div>
      <span id="status-text-nav">Checking…</span>
    </div>
    <span id="last-sync-nav" style="font-size:11px;color:var(--ink-3)"></span>
  </div>
</div>
<!-- Mobile filter bar'''
new_nav_status = '''</div>
<!-- Mobile filter bar'''
if old_nav_status in html:
    html = html.replace(old_nav_status, new_nav_status)
    results.append('Duplicate status removed: OK')
else:
    results.append('Duplicate status: NOT FOUND')

# ── 2. Move synced time below date in masthead; make date larger; remove status-dot-nav JS refs
# Update masthead-right: stack date + synced vertically
old_masthead_right = '''  <div class="masthead-right">
    <div class="date-line" id="date-display"></div>
    <button class="btn btn-outline" onclick="openModal()" id="add-article-btn" style="display:none">+ Add Article</button>
    <button class="btn btn-outline" onclick="openInterviewModal()" id="add-interview-btn" style="display:none">+ Add Interview</button>

  </div>'''
new_masthead_right = '''  <div class="masthead-right" style="flex-direction:column;align-items:flex-end;gap:2px">
    <div class="date-line" id="date-display" style="font-size:13px;color:var(--ink-2)"></div>
    <span id="last-sync-masthead" style="font-size:11px;color:var(--ink-3)"></span>
    <button class="btn btn-outline" onclick="openModal()" id="add-article-btn" style="display:none">+ Add Article</button>
    <button class="btn btn-outline" onclick="openInterviewModal()" id="add-interview-btn" style="display:none">+ Add Interview</button>
  </div>'''
if old_masthead_right in html:
    html = html.replace(old_masthead_right, new_masthead_right)
    results.append('Masthead date+sync: OK')
else:
    results.append('Masthead right: NOT FOUND')

# ── 3. Remove server status from folder-switcher (it's now only in masthead via row 2)
#    Keep the sync time label in folder-switcher but remove the duplicate status dot
old_fs_status = '''    <div class="server-status">
      <div class="status-dot" id="status-dot"></div>
      <span id="status-text" style="font-size:11px;color:var(--ink-3)">Checking server…</span>
    </div>
    <span class="last-sync" id="last-sync-label" style="font-size:11px;color:var(--ink-3)"></span>
    <button class="btn btn-dark" onclick="openAIPanel()" style="background:var(--accent);font-size:11px;padding:5px 14px">✦ AI Analysis</button>'''
new_fs_status = '''    <div class="server-status">
      <div class="status-dot" id="status-dot"></div>
      <span id="status-text" style="font-size:11px;color:var(--ink-3)">Checking server…</span>
    </div>
    <span class="last-sync" id="last-sync-label" style="display:none"></span>
    <button class="btn btn-dark" onclick="openAIPanel()" style="background:var(--accent);font-size:11px;padding:5px 14px">✦ AI Analysis</button>'''
if old_fs_status in html:
    html = html.replace(old_fs_status, new_fs_status)
    results.append('Folder-switcher status cleaned: OK')
else:
    results.append('Folder-switcher status: NOT FOUND')

# ── 4. Also update JS sync label to update masthead span
old_sync_js = "const navSync=document.getElementById('last-sync-nav');if(navSync)navSync.textContent=document.getElementById('last-sync-label').textContent;document.getElementById('last-sync-label').textContent='Synced '+new Date().toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'});"
new_sync_js = "const syncText='Synced '+new Date().toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'});document.getElementById('last-sync-label').textContent=syncText;const mSync=document.getElementById('last-sync-masthead');if(mSync)mSync.textContent=syncText;"
if old_sync_js in html:
    html = html.replace(old_sync_js, new_sync_js)
    results.append('Sync JS updated: OK')
else:
    results.append('Sync JS: NOT FOUND')

# ── 5. Remove background tint from active nav-tab — just bold underline
old_nav_active = '.nav-tab.active { color: var(--ink); font-weight: 500; border-bottom: 3px solid var(--accent); background: var(--accent-light); }'
new_nav_active = '.nav-tab.active { color: var(--ink); font-weight: 600; border-bottom: 3px solid var(--accent); background: none; }'
if old_nav_active in html:
    html = html.replace(old_nav_active, new_nav_active)
    results.append('Nav active no bg: OK')
else:
    results.append('Nav active: NOT FOUND')

# ── 6. Make folder-tab font larger/bolder so row 2 looks more important than row 3
old_folder_tab_css = '''  font-size: 12px;
  font-weight: 500;
  font-family: 'IBM Plex Sans', sans-serif;
  border: none;
  background: none;
  color: var(--ink-3);
  cursor: pointer;
  letter-spacing: 0.2px;'''
new_folder_tab_css = '''  font-size: 13px;
  font-weight: 600;
  font-family: 'IBM Plex Sans', sans-serif;
  border: none;
  background: none;
  color: var(--ink-3);
  cursor: pointer;
  letter-spacing: 0.1px;'''
if old_folder_tab_css in html:
    html = html.replace(old_folder_tab_css, new_folder_tab_css)
    results.append('Folder tab larger: OK')
else:
    results.append('Folder tab font: NOT FOUND')

# And make row 3 (main-nav) smaller/lighter to reduce its visual weight
old_nav_tab = ".nav-tab { padding: 10px 14px; font-size: 12px; color: var(--ink-3); cursor: pointer; border-bottom: 2px solid transparent; white-space: nowrap; letter-spacing: 0.5px; text-transform: uppercase; transition: all 0.15s; background: none; border-top: none; border-left: none; border-right: none; font-family: 'IBM Plex Sans', sans-serif; display: flex; align-items: center; gap: 5px; }"
new_nav_tab = ".nav-tab { padding: 8px 14px; font-size: 11px; color: var(--ink-3); cursor: pointer; border-bottom: 2px solid transparent; white-space: nowrap; letter-spacing: 0.6px; text-transform: uppercase; transition: all 0.15s; background: none; border-top: none; border-left: none; border-right: none; font-family: 'IBM Plex Sans', sans-serif; display: flex; align-items: center; gap: 5px; }"
if old_nav_tab in html:
    html = html.replace(old_nav_tab, new_nav_tab)
    results.append('Nav-tab smaller: OK')
else:
    results.append('Nav-tab: NOT FOUND')

# ── 7. FP — rename to "Foreign Policy" in pill label
old_fp = '<span id="act-fp-pill" class="activity-pill activity-pill-zero"><span style="color:#2d6b45;font-weight:500">FP</span> <span id="act-fp">–</span></span>'
new_fp = '<span id="act-fp-pill" class="activity-pill activity-pill-zero"><span style="color:#2d6b45;font-weight:500">Foreign Policy</span> <span id="act-fp">–</span></span>'
if old_fp in html:
    html = html.replace(old_fp, new_fp)
    results.append('FP renamed: OK')
else:
    results.append('FP pill: NOT FOUND')

# ── 8. Remove amber left border from AI pick cards
old_ai_pick_css = '''.article-card.ai-pick { background: var(--paper); border-left: 3px solid var(--accent); }
.featured-card.ai-pick { background: var(--paper); border-left: 3px solid var(--accent); }'''
new_ai_pick_css = '''.article-card.ai-pick { background: var(--paper); }
.featured-card.ai-pick { background: var(--paper); }'''
if old_ai_pick_css in html:
    html = html.replace(old_ai_pick_css, new_ai_pick_css)
    results.append('AI pick border removed: OK')
else:
    results.append('AI pick border: NOT FOUND')

# ── 9. Remove border from featured card (first/latest article)
old_featured = '.featured-card { background: var(--paper-2); border: 1px solid var(--rule); padding: 18px 20px; margin-bottom: 2px; cursor: pointer; transition: opacity 0.15s; }'
new_featured = '.featured-card { background: var(--paper-2); border: none; border-bottom: 1px solid var(--rule); padding: 18px 20px; margin-bottom: 2px; cursor: pointer; transition: opacity 0.15s; }'
if old_featured in html:
    html = html.replace(old_featured, new_featured)
    results.append('Featured card no border: OK')
else:
    results.append('Featured card: NOT FOUND')

# ── 10. Make rows 1-5 fixed/floating (sticky header)
# Row 1: masthead — already fixed on mobile, need desktop fixed too
# Row 2: folder-switcher
# Row 3: main-nav
# Row 4: info-strip
# Row 5: feed-header-outer (filter row)
# Strategy: add a wrapper class or use CSS on each element

old_masthead_css = ".masthead { border-bottom: 2px solid var(--ink); padding: 14px 20px 10px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }"
new_masthead_css = ".masthead { border-bottom: 2px solid var(--ink); padding: 14px 20px 10px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; position: sticky; top: 0; z-index: 55; background: var(--paper); }"
if old_masthead_css in html:
    html = html.replace(old_masthead_css, new_masthead_css)
    results.append('Masthead sticky: OK')
else:
    results.append('Masthead sticky: NOT FOUND')

old_fs_css = '''#folder-switcher {
  background: var(--paper);
  padding: 8px 20px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--rule);
  gap: 2px;
  z-index: 10;
  position: relative;
}'''
new_fs_css = '''#folder-switcher {
  background: var(--paper);
  padding: 8px 20px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--rule);
  gap: 2px;
  position: sticky;
  top: 57px;
  z-index: 54;
}'''
if old_fs_css in html:
    html = html.replace(old_fs_css, new_fs_css)
    results.append('Folder-switcher sticky: OK')
else:
    results.append('Folder-switcher sticky: NOT FOUND')

old_mainnav_css = ".main-nav { border-bottom: 1px solid var(--rule); padding: 0 20px; display: flex; align-items: center; gap: 0; overflow-x: auto; scrollbar-width: none; }"
new_mainnav_css = ".main-nav { border-bottom: 1px solid var(--rule); padding: 0 20px; display: flex; align-items: center; gap: 0; overflow-x: auto; scrollbar-width: none; position: sticky; top: 101px; z-index: 53; background: var(--paper); }"
if old_mainnav_css in html:
    html = html.replace(old_mainnav_css, new_mainnav_css)
    results.append('Main-nav sticky: OK')
else:
    results.append('Main-nav sticky: NOT FOUND')

# Info strip and filter row — make sticky inline via style attribute update
old_info_strip = '<div id="info-strip" style="display:flex;align-items:center;gap:10px;padding:6px 20px;background:var(--paper-2);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap">'
new_info_strip = '<div id="info-strip" style="display:flex;align-items:center;gap:10px;padding:6px 20px;background:var(--paper-2);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap;position:sticky;top:137px;z-index:52;">'
if old_info_strip in html:
    html = html.replace(old_info_strip, new_info_strip)
    results.append('Info-strip sticky: OK')
else:
    results.append('Info-strip: NOT FOUND')

old_filter_row = '<div id="feed-header-outer" style="display:flex;align-items:center;gap:8px;padding:7px 20px;background:var(--paper);border-bottom:2px solid var(--rule);">'
new_filter_row = '<div id="feed-header-outer" style="display:flex;align-items:center;gap:8px;padding:7px 20px;background:var(--paper);border-bottom:2px solid var(--rule);position:sticky;top:174px;z-index:51;">'
if old_filter_row in html:
    html = html.replace(old_filter_row, new_filter_row)
    results.append('Filter row sticky: OK')
else:
    results.append('Filter row: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
