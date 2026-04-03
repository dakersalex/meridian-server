
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

old = """  const h3 = is_ ? is_.offsetHeight : 0;
  fs.style.top = (h0 - 1) + 'px';
  mn.style.top = (h0 + h1 - 2) + 'px';
  if (is_) is_.style.top = (h0 + h1 + h2 - 3) + 'px';
  const h3actual = (is_ && is_.style.display !== 'none') ? h3 : 0;
  if (fh) fh.style.top = (h0 + h1 + h2 + h3actual - 4) + 'px';"""

new = """  const h3 = fh ? fh.offsetHeight : 0;
  fs.style.top = (h0 - 1) + 'px';
  mn.style.top = (h0 + h1 - 2) + 'px';
  if (fh) fh.style.top = (h0 + h1 + h2 - 3) + 'px';
  const h4actual = (is_ && is_.style.display !== 'none') ? is_.offsetHeight : 0;
  if (is_) is_.style.top = (h0 + h1 + h2 + h3 - 4) + 'px';"""

if old in html:
    html = html.replace(old, new)
    print('recalcStickyTops reordered: OK')
else:
    print('NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)
