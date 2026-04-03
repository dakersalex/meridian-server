
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# Article card — remove opacity hover, add amber border transition
old_card = '.article-card { padding: 0; margin-bottom: 2px; border-bottom: 1px solid var(--rule); cursor: pointer; transition: opacity 0.15s; }'
new_card = '.article-card { padding: 0; margin-bottom: 2px; border-bottom: 1px solid var(--rule); cursor: pointer; border-left: 3px solid transparent; transition: border-left-color 0.15s; }'
if old_card in html:
    html = html.replace(old_card, new_card)
    results.append('article-card: OK')
else:
    results.append('article-card: NOT FOUND')

old_hover = '.article-card:hover { opacity: 0.75; }'
new_hover = '.article-card:hover { border-left-color: var(--accent); }'
if old_hover in html:
    html = html.replace(old_hover, new_hover)
    results.append('article-card hover: OK')
else:
    results.append('article-card hover: NOT FOUND')

# Featured card — same treatment
old_feat = '.featured-card { background: var(--paper-2); border: none; border-bottom: 1px solid var(--rule); padding: 0; margin-bottom: 2px; cursor: pointer; transition: opacity 0.15s; }'
new_feat = '.featured-card { background: var(--paper-2); border: none; border-bottom: 1px solid var(--rule); padding: 0; margin-bottom: 2px; cursor: pointer; border-left: 3px solid transparent; transition: border-left-color 0.15s; }'
if old_feat in html:
    html = html.replace(old_feat, new_feat)
    results.append('featured-card: OK')
else:
    results.append('featured-card: NOT FOUND')

old_feat_hover = '.featured-card:hover { opacity: 0.8; }'
new_feat_hover = '.featured-card:hover { border-left-color: var(--accent); }'
if old_feat_hover in html:
    html = html.replace(old_feat_hover, new_feat_hover)
    results.append('featured-card hover: OK')
else:
    results.append('featured-card hover: NOT FOUND')

# The card-inner padding needs to compensate for the 3px border
# so content doesn't shift left — reduce left padding by 3px
old_inner = '.card-inner { display: flex; gap: 16px; padding: 16px 20px; }'
new_inner = '.card-inner { display: flex; gap: 16px; padding: 16px 20px 16px 17px; }'
if old_inner in html:
    html = html.replace(old_inner, new_inner)
    results.append('card-inner padding: OK')
else:
    results.append('card-inner padding: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
