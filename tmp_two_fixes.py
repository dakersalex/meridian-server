
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# ── Fix 1: All sticky rows need solid opaque backgrounds so content doesn't bleed through
# main-nav already has background:var(--paper) — check info-strip and filter row
# The real issue: info-strip has paper-2 bg but the content below it has paper bg,
# and the sticky rows themselves may not be covering scrolled content.
# Add backdrop to each sticky row explicitly.

# info-strip — already has paper-2, fine
# filter row — already has paper, fine
# The issue is the sidebar heading "SOURCES" showing through — sidebar is not sticky-aware
# Real fix: ensure each sticky element has a non-transparent background + add box-shadow
# to visually separate them from content scrolling underneath

old_mainnav_css = ".main-nav { border-bottom: 1px solid var(--rule); padding: 0 20px; display: flex; align-items: center; gap: 0; overflow-x: auto; scrollbar-width: none; position: sticky; top: 101px; z-index: 53; background: var(--paper); }"
new_mainnav_css = ".main-nav { border-bottom: 1px solid var(--rule); padding: 0 20px; display: flex; align-items: center; gap: 0; overflow-x: auto; scrollbar-width: none; position: sticky; top: 101px; z-index: 53; background: var(--paper); box-shadow: 0 1px 0 var(--rule); }"
if old_mainnav_css in html:
    html = html.replace(old_mainnav_css, new_mainnav_css)
    results.append('main-nav bg: OK')
else:
    results.append('main-nav bg: NOT FOUND')

# folder-switcher — ensure solid bg
old_fs = '''#folder-switcher {
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
new_fs = '''#folder-switcher {
  background: var(--paper);
  padding: 8px 20px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--rule);
  gap: 2px;
  position: sticky;
  top: 57px;
  z-index: 54;
  isolation: isolate;
}'''
if old_fs in html:
    html = html.replace(old_fs, new_fs)
    results.append('folder-switcher isolation: OK')
else:
    results.append('folder-switcher: NOT FOUND')

# info-strip inline style — add box-shadow
old_info = 'display:flex;align-items:center;gap:10px;padding:6px 20px;background:var(--paper-2);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap;position:sticky;top:137px;z-index:52;'
new_info = 'display:flex;align-items:center;gap:10px;padding:6px 20px;background:var(--paper-2);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap;position:sticky;top:137px;z-index:52;isolation:isolate;'
if old_info in html:
    html = html.replace(old_info, new_info)
    results.append('info-strip isolation: OK')
else:
    results.append('info-strip: NOT FOUND')

# filter row inline style — add isolation
old_filter = 'display:flex;align-items:center;gap:8px;padding:7px 20px;background:var(--paper);border-bottom:2px solid var(--rule);position:sticky;top:174px;z-index:51;'
new_filter = 'display:flex;align-items:center;gap:8px;padding:7px 20px;background:var(--paper);border-bottom:2px solid var(--rule);position:sticky;top:174px;z-index:51;isolation:isolate;'
if old_filter in html:
    html = html.replace(old_filter, new_filter)
    results.append('filter-row isolation: OK')
else:
    results.append('filter-row: NOT FOUND')

# ── Fix 2: Featured card — remove side padding so it aligns with regular cards
# feed-area provides the 20px horizontal padding, featured card should not add its own
old_featured_css = '.featured-card { background: var(--paper-2); border: none; border-bottom: 1px solid var(--rule); padding: 18px 20px; margin-bottom: 2px; cursor: pointer; transition: opacity 0.15s; }'
new_featured_css = '.featured-card { background: var(--paper-2); border: none; border-bottom: 1px solid var(--rule); padding: 16px 0; margin-bottom: 2px; cursor: pointer; transition: opacity 0.15s; }'
if old_featured_css in html:
    html = html.replace(old_featured_css, new_featured_css)
    results.append('featured-card padding: OK')
else:
    results.append('featured-card padding: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
