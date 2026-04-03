
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

old = '  <div id="folder-tabs"></div>\n\n</div>\n<!-- Mobile filter bar'
new = '''  <div id="folder-tabs"></div>
  <div style="margin-left:auto;display:flex;align-items:center;gap:10px;padding-right:4px">
    <div style="display:flex;align-items:center;gap:5px;font-size:11px;color:var(--ink-3)">
      <div class="status-dot" id="status-dot-nav"></div>
      <span id="status-text-nav">Checking…</span>
    </div>
    <span id="last-sync-nav" style="font-size:11px;color:var(--ink-3)"></span>
  </div>
</div>
<!-- Mobile filter bar'''

if old in html:
    html = html.replace(old, new)
    print('Main nav status: OK')
else:
    print('NOT FOUND — checking actual bytes')
    idx = html.find('folder-tabs')
    print(repr(html[idx:idx+80]))

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)
