
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# ── 1. Move server status from folder-switcher to masthead-right
# Remove from folder-switcher
old_fs_status = '''  <div style="margin-left:auto;display:flex;align-items:center;gap:12px">
    <div class="server-status">
      <div class="status-dot" id="status-dot"></div>
      <span id="status-text" style="font-size:11px;color:var(--ink-3)">Checking server…</span>
    </div>
    <span class="last-sync" id="last-sync-label" style="display:none"></span>
    <button class="btn btn-dark" onclick="openAIPanel()" style="background:var(--accent);font-size:11px;padding:5px 14px">✦ AI Analysis</button>
    <button class="btn btn-dark mobile-sync-btn" onclick="syncAll()" style="display:none;background:var(--accent);font-size:11px;padding:4px 10px">🔄 Sync</button>
  </div>'''
new_fs_status = '''  <div style="margin-left:auto;display:flex;align-items:center;gap:12px">
    <span class="last-sync" id="last-sync-label" style="display:none"></span>
    <button class="btn btn-dark" onclick="openAIPanel()" style="background:var(--accent);font-size:11px;padding:5px 14px">✦ AI Analysis</button>
    <button class="btn btn-dark mobile-sync-btn" onclick="syncAll()" style="display:none;background:var(--accent);font-size:11px;padding:4px 10px">🔄 Sync</button>
  </div>'''
if old_fs_status in html:
    html = html.replace(old_fs_status, new_fs_status)
    results.append('Status removed from folder-switcher: OK')
else:
    results.append('folder-switcher status: NOT FOUND')

# Add to masthead-right — below date/sync, above buttons
old_masthead_right = '''  <div class="masthead-right" style="flex-direction:column;align-items:flex-end;gap:2px">
    <div class="date-line" id="date-display" style="font-size:13px;color:var(--ink-2)"></div>
    <span id="last-sync-masthead" style="font-size:11px;color:var(--ink-3)"></span>
    <button class="btn btn-outline" onclick="openModal()" id="add-article-btn" style="display:none">+ Add Article</button>
    <button class="btn btn-outline" onclick="openInterviewModal()" id="add-interview-btn" style="display:none">+ Add Interview</button>
  </div>'''
new_masthead_right = '''  <div class="masthead-right" style="flex-direction:column;align-items:flex-end;gap:2px">
    <div class="date-line" id="date-display" style="font-size:13px;color:var(--ink-2)"></div>
    <div style="display:flex;align-items:center;gap:6px">
      <span id="last-sync-masthead" style="font-size:11px;color:var(--ink-3)"></span>
      <div class="server-status" style="font-size:11px">
        <div class="status-dot" id="status-dot"></div>
        <span id="status-text" style="font-size:11px;color:var(--ink-3)">Checking…</span>
      </div>
    </div>
    <button class="btn btn-outline" onclick="openModal()" id="add-article-btn" style="display:none">+ Add Article</button>
    <button class="btn btn-outline" onclick="openInterviewModal()" id="add-interview-btn" style="display:none">+ Add Interview</button>
  </div>'''
if old_masthead_right in html:
    html = html.replace(old_masthead_right, new_masthead_right)
    results.append('Status added to masthead: OK')
else:
    results.append('masthead-right: NOT FOUND')

# ── 2. Fix sidebar — sticky with correct top offset
# The sidebar's top: 0 means it sticks at the very top of the viewport,
# behind all the sticky header rows. It needs to stick below them.
# We compute this in JS via recalcStickyTops.
# But also set a sensible CSS default.
old_sidebar_css = '.sidebar { padding: 16px; border-left: 1px solid var(--rule); position: sticky; top: 0; height: 100vh; overflow-y: auto; align-self: start; }'
new_sidebar_css = '.sidebar { padding: 16px; border-left: 1px solid var(--rule); position: sticky; top: 225px; height: calc(100vh - 225px); overflow-y: auto; align-self: start; }'
if old_sidebar_css in html:
    html = html.replace(old_sidebar_css, new_sidebar_css)
    results.append('Sidebar sticky top: OK')
else:
    results.append('Sidebar sticky: NOT FOUND')

# ── 3. Update recalcStickyTops to also set sidebar top dynamically
old_recalc = '''  if (fh) fh.style.top = (h0 + h1 + h2 + h3 - 4) + 'px';
}'''
new_recalc = '''  if (fh) fh.style.top = (h0 + h1 + h2 + h3 - 4) + 'px';
  // Sidebar sticks below all header rows
  const h4 = fh ? fh.offsetHeight : 0;
  const totalHeaderH = h0 + h1 + h2 + h3 + h4 - 4;
  const sidebar = document.querySelector('.sidebar');
  if (sidebar) {
    sidebar.style.top = totalHeaderH + 'px';
    sidebar.style.height = (window.innerHeight - totalHeaderH) + 'px';
  }
}'''
if old_recalc in html:
    html = html.replace(old_recalc, new_recalc)
    results.append('Sidebar in recalc: OK')
else:
    results.append('Sidebar recalc: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
