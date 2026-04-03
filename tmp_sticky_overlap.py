
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

# Update recalcStickyTops to subtract 1px from each top so rows slightly overlap
# This eliminates any sub-pixel gap from browser rendering
old_fn = """function recalcStickyTops() {
  const masthead = document.querySelector('.masthead');
  const fs = document.getElementById('folder-switcher');
  const mn = document.getElementById('main-nav');
  const is_ = document.getElementById('info-strip');
  const fh = document.getElementById('feed-header-outer');
  if (!masthead || !fs || !mn) return;
  const h0 = masthead.offsetHeight;
  const h1 = fs.offsetHeight;
  const h2 = mn.offsetHeight;
  const h3 = is_ ? is_.offsetHeight : 0;
  fs.style.top = h0 + 'px';
  mn.style.top = (h0 + h1) + 'px';
  if (is_) is_.style.top = (h0 + h1 + h2) + 'px';
  if (fh) fh.style.top = (h0 + h1 + h2 + h3) + 'px';
}"""

new_fn = """function recalcStickyTops() {
  const masthead = document.querySelector('.masthead');
  const fs = document.getElementById('folder-switcher');
  const mn = document.getElementById('main-nav');
  const is_ = document.getElementById('info-strip');
  const fh = document.getElementById('feed-header-outer');
  if (!masthead || !fs || !mn) return;
  const h0 = masthead.offsetHeight;
  const h1 = fs.offsetHeight;
  const h2 = mn.offsetHeight;
  const h3 = is_ ? is_.offsetHeight : 0;
  fs.style.top = (h0 - 1) + 'px';
  mn.style.top = (h0 + h1 - 2) + 'px';
  if (is_) is_.style.top = (h0 + h1 + h2 - 3) + 'px';
  if (fh) fh.style.top = (h0 + h1 + h2 + h3 - 4) + 'px';
}"""

if old_fn in html:
    html = html.replace(old_fn, new_fn)
    print('overlap fix: OK')
else:
    print('NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)
