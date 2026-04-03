
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# Fix 1: restore info-strip to 'flex' not '' when returning to newsfeed
old = "    if (infoStrip)  infoStrip.style.display = '';\n    mainNav.style.display = '';"
new = "    if (infoStrip)  infoStrip.style.display = 'flex';\n    mainNav.style.display = 'flex';"
if old in html:
    html = html.replace(old, new)
    results.append('infoStrip display flex: OK')
else:
    results.append('infoStrip display: NOT FOUND')

# Fix 2: restore feedHeader to 'flex' not '' when returning to newsfeed
old2 = "    if (feedHeader) feedHeader.style.display = '';\n    if (infoStrip)"
new2 = "    if (feedHeader) feedHeader.style.display = 'flex';\n    if (infoStrip)"
if old2 in html:
    html = html.replace(old2, new2)
    results.append('feedHeader display flex: OK')
else:
    results.append('feedHeader display: NOT FOUND')

# Fix 3: also restore mainLayout properly
old3 = "    if (mainLayout) mainLayout.style.display = '';\n    if (feedHeader) feedHeader.style.display = 'flex';"
new3 = "    if (mainLayout) mainLayout.style.display = 'grid';\n    if (feedHeader) feedHeader.style.display = 'flex';"
if old3 in html:
    html = html.replace(old3, new3)
    results.append('mainLayout display grid: OK')
else:
    results.append('mainLayout display: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
