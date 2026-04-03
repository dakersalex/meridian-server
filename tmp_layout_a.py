
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# ─────────────────────────────────────────────
# 1. Remove "+ Add Article" button from masthead
# ─────────────────────────────────────────────
old_add_article = '''    <button class="btn btn-outline" onclick="openModal()" id="add-article-btn">+ Add Article</button>
    <button class="btn btn-outline" onclick="openInterviewModal()" id="add-interview-btn" style="display:none">+ Add Interview</button>'''
new_add_article = '''    <button class="btn btn-outline" onclick="openModal()" id="add-article-btn" style="display:none">+ Add Article</button>
    <button class="btn btn-outline" onclick="openInterviewModal()" id="add-interview-btn" style="display:none">+ Add Interview</button>'''
if old_add_article in html:
    html = html.replace(old_add_article, new_add_article)
    results.append('Add Article hidden: OK')
else:
    results.append('Add Article: NOT FOUND')

# ─────────────────────────────────────────────
# 2. Remove "+ New Folder" button from main-nav
# ─────────────────────────────────────────────
old_new_folder = '  <button class="add-folder-btn" onclick="promptNewFolder()">+ New Folder</button>'
new_new_folder = ''
if old_new_folder in html:
    html = html.replace(old_new_folder, new_new_folder)
    results.append('New Folder removed: OK')
else:
    results.append('New Folder: NOT FOUND')

# ─────────────────────────────────────────────
# 3. Upgrade main-nav: stronger active tab, server status moved here
#    Also add server status row inline with sub-nav
# ─────────────────────────────────────────────
old_mainnav = '''<div class="main-nav" id="main-nav">
  <button class="nav-tab active" onclick="setView('feed',this)">Feed <span class="nav-count" id="count-feed">0</span></button>
  <button class="nav-tab" onclick="setView('archive',this)">Archive <span class="nav-count" id="count-archive">0</span></button>
  <button class="nav-tab" onclick="setView('newsletters',this)">Newsletters <span class="nav-count" id="count-newsletters">0</span></button>
  <button class="nav-tab" onclick="setView('interviews',this)">Interviews <span class="nav-count" id="count-interviews">0</span></button>
  <button class="nav-tab" onclick="setView('suggested',this)">Suggested <span class="nav-count" id="count-suggested">0</span></button>
  <div id="folder-tabs"></div>
  
</div>'''
new_mainnav = '''<div class="main-nav" id="main-nav">
  <button class="nav-tab active" onclick="setView('feed',this)">Feed <span class="nav-count" id="count-feed">0</span></button>
  <button class="nav-tab" onclick="setView('archive',this)">Archive <span class="nav-count" id="count-archive">0</span></button>
  <button class="nav-tab" onclick="setView('newsletters',this)">Newsletters <span class="nav-count" id="count-newsletters">0</span></button>
  <button class="nav-tab" onclick="setView('interviews',this)">Interviews <span class="nav-count" id="count-interviews">0</span></button>
  <button class="nav-tab" onclick="setView('suggested',this)">Suggested <span class="nav-count" id="count-suggested">0</span></button>
  <div id="folder-tabs"></div>
  <div style="margin-left:auto;display:flex;align-items:center;gap:10px;padding-right:4px">
    <div style="display:flex;align-items:center;gap:5px;font-size:11px;color:var(--ink-3)">
      <div class="status-dot" id="status-dot-nav"></div>
      <span id="status-text-nav">Checking…</span>
    </div>
    <span id="last-sync-nav" style="font-size:11px;color:var(--ink-3)"></span>
  </div>
</div>'''
if old_mainnav in html:
    html = html.replace(old_mainnav, new_mainnav)
    results.append('Main nav upgraded: OK')
else:
    results.append('Main nav: NOT FOUND')

# ─────────────────────────────────────────────
# 4. Replace feed-header (filter row) with clearly distinct styled version
#    Remove select-all/delete-selected (kept hidden for JS compat)
# ─────────────────────────────────────────────
old_feed_header = '''<!-- feed-header outside feed-area so it doesn't affect document flow -->
<div class="feed-header" id="feed-header-outer">
  <span class="feed-title" id="feed-title" style="display:none"></span>
  <div class="feed-controls" style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
    <select class="filter-select" id="status-filter" onchange="renderFeed()"><option value="all">All articles</option><option value="full_text">Full text only</option><option value="title_only">Title only</option></select>
    <select class="filter-select" id="curation-filter" onchange="renderFeed()">
      <option value="all">All articles</option>
      <option value="saved">My saves</option>
      <option value="ai">AI suggested</option>
    </select>
    <select class="filter-select" id="source-filter" onchange="renderFeed()">
      <option value="all">All sources</option>
      <option value="Financial Times">FT</option>
      <option value="The Economist">Economist</option>
      <option value="Foreign Affairs">Foreign Affairs</option>
      <option value="Bloomberg">Bloomberg</option>
    </select>
    <select class="filter-select" id="date-filter" onchange="renderFeed()">
      <option value="180">Last 6 months</option>
      <option value="30">Last 30 days</option>
      <option value="7">Last 7 days</option>
      <option value="365">Last year</option>
      <option value="9999">All time</option>
    </select>
    <div style="margin-left:auto;display:flex;gap:4px;align-items:center">
      <button class="btn btn-outline" onclick="selectAll()" style="font-size:11px;padding:4px 8px" id="select-all-btn">Select all</button>
      <button class="btn btn-outline" onclick="deleteSelected()" style="font-size:11px;padding:4px 8px;display:none;border-color:var(--red);color:var(--red)" id="delete-selected-btn">Delete selected</button>
    </div>
  </div>
</div>'''

new_feed_header = '''<!-- filter row — visually distinct from info strip above -->
<div id="feed-header-outer" style="display:flex;align-items:center;gap:8px;padding:7px 20px;background:var(--paper);border-bottom:2px solid var(--rule);">
  <span style="font-size:10px;font-weight:500;letter-spacing:0.8px;text-transform:uppercase;color:var(--ink-3);margin-right:4px">Filter</span>
  <span class="feed-title" id="feed-title" style="display:none"></span>
  <select class="filter-select" id="status-filter" onchange="renderFeed()"><option value="all">All articles</option><option value="full_text">Full text only</option><option value="title_only">Title only</option></select>
  <select class="filter-select" id="curation-filter" onchange="renderFeed()">
    <option value="all">All curation</option>
    <option value="saved">My saves</option>
    <option value="ai">AI picks</option>
  </select>
  <select class="filter-select" id="source-filter" onchange="renderFeed()">
    <option value="all">All sources</option>
    <option value="Financial Times">FT</option>
    <option value="The Economist">Economist</option>
    <option value="Foreign Affairs">Foreign Affairs</option>
    <option value="Bloomberg">Bloomberg</option>
  </select>
  <select class="filter-select" id="date-filter" onchange="renderFeed()">
    <option value="180">Last 6 months</option>
    <option value="30">Last 30 days</option>
    <option value="7">Last 7 days</option>
    <option value="365">Last year</option>
    <option value="9999">All time</option>
  </select>
  <button class="btn btn-outline" onclick="selectAll()" style="font-size:11px;padding:4px 8px;display:none" id="select-all-btn">Select all</button>
  <button class="btn btn-outline" onclick="deleteSelected()" style="font-size:11px;padding:4px 8px;display:none;border-color:var(--red);color:var(--red)" id="delete-selected-btn">Delete selected</button>
</div>'''

if old_feed_header in html:
    html = html.replace(old_feed_header, new_feed_header)
    results.append('Filter row redesigned: OK')
else:
    results.append('Filter row: NOT FOUND')

# ─────────────────────────────────────────────
# 5. Make sidebar sticky + fix feed-area padding for gaps between cards
# ─────────────────────────────────────────────
old_sidebar_css = '.sidebar { padding: 16px; border-left: 1px solid var(--rule); }'
new_sidebar_css = '.sidebar { padding: 16px; border-left: 1px solid var(--rule); position: sticky; top: 0; height: 100vh; overflow-y: auto; align-self: start; }'
if old_sidebar_css in html:
    html = html.replace(old_sidebar_css, new_sidebar_css)
    results.append('Sidebar sticky: OK')
else:
    results.append('Sidebar sticky: NOT FOUND')

# ─────────────────────────────────────────────
# 6. Article card — add gap between cards and consistent left indent
#    Cards currently have padding:14px 0 — change to padding:16px 0 with margin-bottom for gap
# ─────────────────────────────────────────────
old_card_css = '.article-card { padding: 14px 0; border-bottom: 1px solid var(--rule); cursor: pointer; transition: opacity 0.15s; }'
new_card_css = '.article-card { padding: 16px 0; margin-bottom: 2px; border-bottom: 1px solid var(--rule); cursor: pointer; transition: opacity 0.15s; }'
if old_card_css in html:
    html = html.replace(old_card_css, new_card_css)
    results.append('Article card gaps: OK')
else:
    results.append('Article card gaps: NOT FOUND')

# Feed area — remove its own top padding since filter row provides separation
old_feed_area = '.feed-area { padding: 20px; border-right: 1px solid var(--rule); }'
new_feed_area = '.feed-area { padding: 0 20px 20px; border-right: 1px solid var(--rule); }'
if old_feed_area in html:
    html = html.replace(old_feed_area, new_feed_area)
    results.append('Feed area padding: OK')
else:
    results.append('Feed area padding: NOT FOUND')

# Feed counter — give it top padding so it sits nicely
old_feed_counter = '<div id="feed-counter" style="font-size:11px;color:var(--ink-3);margin-bottom:10px;"></div>'
new_feed_counter = '<div id="feed-counter" style="font-size:11px;color:var(--ink-3);padding:12px 0 8px;border-bottom:1px solid var(--rule);margin-bottom:12px;"></div>'
if old_feed_counter in html:
    html = html.replace(old_feed_counter, new_feed_counter)
    results.append('Feed counter styled: OK')
else:
    results.append('Feed counter: NOT FOUND')

# ─────────────────────────────────────────────
# 7. Strengthen active nav-tab indicator — thicker bottom border + bg tint
# ─────────────────────────────────────────────
old_nav_active = '.nav-tab.active { color: var(--ink); font-weight: 500; border-bottom: 2px solid var(--accent); }'
new_nav_active = '.nav-tab.active { color: var(--ink); font-weight: 500; border-bottom: 3px solid var(--accent); background: var(--accent-light); }'
if old_nav_active in html:
    html = html.replace(old_nav_active, new_nav_active)
    results.append('Nav active stronger: OK')
else:
    results.append('Nav active: NOT FOUND')

# ─────────────────────────────────────────────
# 8. Sync server status elements to also update the new nav copies
# ─────────────────────────────────────────────
old_status_js = "serverOnline=true;document.getElementById('status-dot').className='status-dot connected';document.getElementById('status-text').textContent='meridianreader.com · connected';return true;"
new_status_js = "serverOnline=true;document.getElementById('status-dot').className='status-dot connected';document.getElementById('status-text').textContent='meridianreader.com · connected';const nd=document.getElementById('status-dot-nav');if(nd)nd.className='status-dot connected';const nt=document.getElementById('status-text-nav');if(nt)nt.textContent='meridianreader.com · connected';return true;"
if old_status_js in html:
    html = html.replace(old_status_js, new_status_js)
    results.append('Status dot nav sync: OK')
else:
    results.append('Status dot nav: NOT FOUND')

old_status_offline = "serverOnline=false;document.getElementById('status-dot').className='status-dot error';document.getElementById('status-text').textContent='Server offline — check systemctl status meridian on VPS';return false;"
new_status_offline = "serverOnline=false;document.getElementById('status-dot').className='status-dot error';document.getElementById('status-text').textContent='Server offline — check systemctl status meridian on VPS';const nd2=document.getElementById('status-dot-nav');if(nd2)nd2.className='status-dot error';const nt2=document.getElementById('status-text-nav');if(nt2)nt2.textContent='Server offline';return false;"
if old_status_offline in html:
    html = html.replace(old_status_offline, new_status_offline)
    results.append('Offline status nav: OK')
else:
    results.append('Offline status nav: NOT FOUND')

# Also sync last-sync label to nav copy
old_sync_label = "document.getElementById('last-sync-label').textContent"
new_sync_label = "const navSync=document.getElementById('last-sync-nav');if(navSync)navSync.textContent=document.getElementById('last-sync-label').textContent;document.getElementById('last-sync-label').textContent"
if old_sync_label in html:
    html = html.replace(old_sync_label, new_sync_label, 1)  # only first occurrence
    results.append('Sync label nav: OK')
else:
    results.append('Sync label nav: NOT FOUND')

# ─────────────────────────────────────────────
# 9. Featured card — remove the extra margin-bottom that creates uneven gap
#    and make it consistent with regular cards
# ─────────────────────────────────────────────
old_featured_css = '.featured-card { background: var(--paper-2); border: 1px solid var(--rule); padding: 18px; margin-bottom: 14px; cursor: pointer; transition: opacity 0.15s; }'
new_featured_css = '.featured-card { background: var(--paper-2); border: 1px solid var(--rule); padding: 18px 20px; margin-bottom: 2px; cursor: pointer; transition: opacity 0.15s; }'
if old_featured_css in html:
    html = html.replace(old_featured_css, new_featured_css)
    results.append('Featured card consistent: OK')
else:
    results.append('Featured card: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
