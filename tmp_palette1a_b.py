
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# Remove status from main-nav (the duplicate in row 3)
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
    results.append('Nav status removed: OK')
else:
    # Already removed in a previous session
    results.append('Nav status: already clean')

# Sidebar also white background
old_sidebar = '.sidebar { padding: 16px; border-left: 1px solid var(--rule); position: sticky; top: 0; height: 100vh; overflow-y: auto; align-self: start; }'
new_sidebar = '.sidebar { padding: 16px; border-left: 1px solid var(--rule); position: sticky; top: 0; height: 100vh; overflow-y: auto; align-self: start; background: #ffffff; }'
if old_sidebar in html:
    html = html.replace(old_sidebar, new_sidebar)
    results.append('Sidebar white: OK')
else:
    results.append('Sidebar: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
