
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

old = '''    <select class="filter-select" id="source-filter" onchange="renderFeed()">
      <option value="all">All sources</option>
      <option value="Financial Times">FT</option>
      <option value="The Economist">Economist</option>
      <option value="Foreign Affairs">Foreign Affairs</option>
    </select>'''

new = '''    <select class="filter-select" id="source-filter" onchange="renderFeed()">
      <option value="all">All sources</option>
      <option value="Financial Times">FT</option>
      <option value="The Economist">Economist</option>
      <option value="Foreign Affairs">Foreign Affairs</option>
      <option value="Bloomberg">Bloomberg</option>
    </select>'''

if old in html:
    html = html.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print('PATCHED OK')
else:
    print('NOT FOUND')
