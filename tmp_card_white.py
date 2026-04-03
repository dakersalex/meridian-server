
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# article-card needs explicit white background
old = '.article-card { padding: 0; margin-bottom: 2px; border-bottom: 1px solid var(--rule); cursor: pointer; border-left: 3px solid transparent; transition: border-left-color 0.15s; }'
new = '.article-card { padding: 0; margin-bottom: 0; border-bottom: 1px solid var(--rule); cursor: pointer; border-left: 3px solid transparent; transition: border-left-color 0.15s; background: #ffffff; }'
if old in html:
    html = html.replace(old, new)
    results.append('article-card white: OK')
else:
    results.append('article-card: NOT FOUND')

# Feed header outer (filter row) stays paper — already correct
# body background should stay paper for the outer chrome
# But change --paper to make the contrast a bit clearer
# Actually just ensure the body bg and header rows read as clearly different from white
# The real issue: body is #faf8f4, cards should be #ffffff — contrast is subtle
# Make it clearer by darkening the header background slightly
old_paper = '  --paper: #faf8f4; --paper-2: #f2efe8; --paper-3: #e8e4da;'
new_paper = '  --paper: #f5f2ec; --paper-2: #ede9e0; --paper-3: #e4dfd4;'
if old_paper in html:
    html = html.replace(old_paper, new_paper)
    results.append('paper darker: OK')
else:
    results.append('paper: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
