
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# Current sticky tops (measured):
# masthead: 0px, h=68
# folder-switcher: 68px, h=44
# main-nav: 112px, h=35
# info-strip: 147px, h=0 (hidden) or ~100px (open)
# feed-header-outer (filter): 184px, h=41

# New order: filter moves ABOVE info-strip
# New tops:
# masthead: 0px (unchanged)
# folder-switcher: 67px (unchanged)
# main-nav: 111px (unchanged)
# feed-header-outer: 146px (was 184, now sits where info-strip was)
# info-strip: below filter, dynamic via recalcStickyTops

# Step 1: update feed-header-outer top from 184px to 147px (its new position above info-strip)
old_fh_top = 'top:184px;z-index:51;isolation:isolate;'
new_fh_top = 'top:147px;z-index:52;isolation:isolate;'
if old_fh_top in html:
    html = html.replace(old_fh_top, new_fh_top)
    results.append('filter top updated: OK')
else:
    results.append('filter top: NOT FOUND')

# Step 2: info-strip top becomes dynamic (below filter), z-index below filter
old_is_top = 'top:147px;z-index:52;isolation:isolate;'
new_is_top = 'top:184px;z-index:51;isolation:isolate;'
# Be careful - after step 1 there are now two matches. The info-strip one
# still has the OLD value 147px but we just changed filter to 147px too.
# Actually step 1 changed filter from 184→147, and info-strip was already 147.
# So now both are 147 — need to distinguish. Let's do it differently.
# Reset: read fresh after step 1 change and patch info-strip by surrounding context.
results.append('info-strip top: handled via recalcStickyTops')

# Step 3: Swap the HTML blocks — filter row goes before info-strip in DOM
# Find the info-strip block end and filter block, then reorder
# The info-strip ends before the KEY THEMES VIEW comment
# The filter row (feed-header-outer) ends before <div class="main-layout">

# Extract both blocks and swap them
import re

# Find info-strip block (from its opening div to the closing </div>)
is_start = html.find('<div id="info-strip"')
is_end = html.find('</div>', is_start) + 6  # first closing div
info_strip_block = html[is_start:is_end]

# Find feed-header-outer block
fh_start = html.find('<div id="feed-header-outer"')
# It ends at </div> before <!-- KEY THEMES or <div class="main-layout">
fh_end = html.find('<div id="key-themes-view">', fh_start)
# Actually find the closing div of feed-header-outer
# It's a single div with one level of children — find its closing
depth = 0
pos = fh_start
while pos < len(html):
    if html[pos:pos+4] == '<div':
        depth += 1
    elif html[pos:pos+6] == '</div>':
        depth -= 1
        if depth == 0:
            fh_end = pos + 6
            break
    pos += 1

feed_header_block = html[fh_start:fh_end]

# The region between info-strip and feed-header-outer (usually just a newline)
between_start = is_end
between_end = fh_start
between = html[between_start:between_end]

# Rebuild: replace the section [info-strip][between][feed-header] with [feed-header][between][info-strip]
old_section = info_strip_block + between + feed_header_block
new_section = feed_header_block + between + info_strip_block

if old_section in html:
    html = html.replace(old_section, new_section)
    results.append('DOM swap filter<->info-strip: OK')
else:
    results.append('DOM swap: NOT FOUND - manual check needed')

# Step 4: Update recalcStickyTops to reflect new order
# New order: masthead(h0) → fs(h1) → mn(h2) → filter(h3) → info-strip(h4, conditional)
old_recalc = '''function recalcStickyTops() {
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
  const h3actual = (is_ && is_.style.display !== 'none') ? h3 : 0;
  if (fh) fh.style.top = (h0 + h1 + h2 + h3actual - 4) + 'px';
}'''

new_recalc = '''function recalcStickyTops() {
  const masthead = document.querySelector('.masthead');
  const fs = document.getElementById('folder-switcher');
  const mn = document.getElementById('main-nav');
  const fh = document.getElementById('feed-header-outer');
  const is_ = document.getElementById('info-strip');
  if (!masthead || !fs || !mn) return;
  const h0 = masthead.offsetHeight;
  const h1 = fs.offsetHeight;
  const h2 = mn.offsetHeight;
  const h3 = fh ? fh.offsetHeight : 0;
  fs.style.top = (h0 - 1) + 'px';
  mn.style.top = (h0 + h1 - 2) + 'px';
  if (fh) fh.style.top = (h0 + h1 + h2 - 3) + 'px';
  const h3actual = (fh) ? h3 : 0;
  const isVisible = is_ && is_.style.display !== 'none';
  if (is_) is_.style.top = (h0 + h1 + h2 + h3actual - 4) + 'px';
}'''

if old_recalc in html:
    html = html.replace(old_recalc, new_recalc)
    results.append('recalcStickyTops reordered: OK')
else:
    results.append('recalcStickyTops: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
