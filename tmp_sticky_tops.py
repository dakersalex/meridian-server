
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# Fix all sticky top values based on actual measured heights:
# masthead: 68px
# folder-switcher: top 68px (was 57)
# main-nav: top 112px (was 101) = 68+44
# info-strip: top 147px (was 137) = 68+44+35
# filter row: top 184px (was 174) = 68+44+35+37

old_fs = '  top: 57px;\n  z-index: 54;'
new_fs = '  top: 68px;\n  z-index: 54;'
if old_fs in html:
    html = html.replace(old_fs, new_fs)
    results.append('folder-switcher top: OK')
else:
    results.append('folder-switcher top: NOT FOUND')

old_mn = 'position: sticky; top: 101px; z-index: 53; background: var(--paper); box-shadow: 0 1px 0 var(--rule);'
new_mn = 'position: sticky; top: 112px; z-index: 53; background: var(--paper); box-shadow: 0 1px 0 var(--rule);'
if old_mn in html:
    html = html.replace(old_mn, new_mn)
    results.append('main-nav top: OK')
else:
    results.append('main-nav top: NOT FOUND')

old_is = 'position:sticky;top:137px;z-index:52;isolation:isolate;'
new_is = 'position:sticky;top:147px;z-index:52;isolation:isolate;'
if old_is in html:
    html = html.replace(old_is, new_is)
    results.append('info-strip top: OK')
else:
    results.append('info-strip top: NOT FOUND')

old_fr = 'position:sticky;top:174px;z-index:51;isolation:isolate;'
new_fr = 'position:sticky;top:184px;z-index:51;isolation:isolate;'
if old_fr in html:
    html = html.replace(old_fr, new_fr)
    results.append('filter-row top: OK')
else:
    results.append('filter-row top: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
