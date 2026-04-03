
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# With info-strip hidden, filter row moves up by ~37px (info-strip height)
# old top for info-strip: 147px, filter row: 184px
# new filter row top when strip hidden: 147px
# But recalcStickyTops() handles this dynamically — just make sure
# info-strip top is still set correctly when visible.
# The recalcStickyTops will measure offsetHeight=0 when display:none, so
# filter row will naturally snap up. That's correct behaviour.

# Also need to update recalcStickyTops to account for info-strip being 0 height when hidden
old_calc = '''  fs.style.top = (h0 - 1) + 'px';
  mn.style.top = (h0 + h1 - 2) + 'px';
  if (is_) is_.style.top = (h0 + h1 + h2 - 3) + 'px';
  if (fh) fh.style.top = (h0 + h1 + h2 + h3 - 4) + 'px';'''

new_calc = '''  fs.style.top = (h0 - 1) + 'px';
  mn.style.top = (h0 + h1 - 2) + 'px';
  if (is_) is_.style.top = (h0 + h1 + h2 - 3) + 'px';
  const h3actual = (is_ && is_.style.display !== 'none') ? h3 : 0;
  if (fh) fh.style.top = (h0 + h1 + h2 + h3actual - 4) + 'px';'''

if old_calc in html:
    html = html.replace(old_calc, new_calc)
    results.append('recalcStickyTops strip-aware: OK')
else:
    results.append('recalcStickyTops: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
