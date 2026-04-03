
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# The approach: stop fighting background colours on individual elements.
# Set ONE content background colour everywhere in the content zone.
# Header rows (sticky) stay darker warm cream.
# Content zone (body / feed-area / cards / sidebar) all = same colour.
# Use the original --paper (#faf8f4) for content, --paper-2 (#ede9e0) for headers.

# 1. Revert paper darkening — restore original warm values
old_paper = '  --paper: #f5f2ec; --paper-2: #ede9e0; --paper-3: #e4dfd4;'
new_paper = '  --paper: #faf8f4; --paper-2: #f0ece3; --paper-3: #e4dfd4;'
if old_paper in html:
    html = html.replace(old_paper, new_paper)
    results.append('paper restored: OK')
else:
    results.append('paper: NOT FOUND')

# 2. All sticky header rows explicitly use --paper-2 (darker warm)
# masthead
old_mast = 'background: var(--paper); }  /* masthead */'
# Actually just set it in the CSS rules directly
# masthead already has background: var(--paper) — change to paper-2
old_mast_css = '.masthead { border-bottom: 2px solid var(--ink); padding: 14px 20px 10px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; position: sticky; top: 0; z-index: 55; background: var(--paper); }'
new_mast_css = '.masthead { border-bottom: 2px solid var(--ink); padding: 14px 20px 10px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; position: sticky; top: 0; z-index: 55; background: var(--paper-2); }'
if old_mast_css in html:
    html = html.replace(old_mast_css, new_mast_css)
    results.append('masthead paper-2: OK')
else:
    results.append('masthead: NOT FOUND')

# folder-switcher (row 2)
old_fs_css = '''#folder-switcher {
  background: var(--paper);'''
new_fs_css = '''#folder-switcher {
  background: var(--paper-2);'''
if old_fs_css in html:
    html = html.replace(old_fs_css, new_fs_css)
    results.append('folder-switcher paper-2: OK')
else:
    results.append('folder-switcher: NOT FOUND')

# main-nav (row 3)
old_mn_css = 'background: var(--paper); box-shadow: 0 1px 0 var(--rule);'
new_mn_css = 'background: var(--paper-2); box-shadow: 0 1px 0 var(--rule);'
if old_mn_css in html:
    html = html.replace(old_mn_css, new_mn_css)
    results.append('main-nav paper-2: OK')
else:
    results.append('main-nav: NOT FOUND')

# info-strip (row 4)
old_info = 'background:var(--paper);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap;position:sticky;top:147px;z-index:52;isolation:isolate;'
new_info = 'background:var(--paper-2);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap;position:sticky;top:147px;z-index:52;isolation:isolate;'
if old_info in html:
    html = html.replace(old_info, new_info)
    results.append('info-strip paper-2: OK')
else:
    results.append('info-strip: NOT FOUND')

# feed-header-outer (filter row 5)
old_fh = 'background:var(--paper);border-bottom:2px solid var(--rule);position:sticky;top:184px;z-index:51;isolation:isolate;'
new_fh = 'background:var(--paper-2);border-bottom:2px solid var(--rule);position:sticky;top:184px;z-index:51;isolation:isolate;'
if old_fh in html:
    html = html.replace(old_fh, new_fh)
    results.append('filter row paper-2: OK')
else:
    results.append('filter row: NOT FOUND')

# 3. Content zone — body, feed-area, cards, sidebar all = var(--paper)
# Body already uses var(--paper) ✓
# feed-area: remove explicit white
old_feed = '.feed-area { padding: 0 20px 20px; border-right: 1px solid var(--rule); background: #ffffff; }'
new_feed = '.feed-area { padding: 0 20px 20px; border-right: 1px solid var(--rule); background: var(--paper); }'
if old_feed in html:
    html = html.replace(old_feed, new_feed)
    results.append('feed-area paper: OK')
else:
    results.append('feed-area: NOT FOUND')

# article-card: remove explicit white, use var(--paper)
old_acard = '.article-card { padding: 0; margin-bottom: 0; border-bottom: 1px solid var(--rule); cursor: pointer; border-left: 3px solid transparent; transition: border-left-color 0.15s; background: #ffffff; }'
new_acard = '.article-card { padding: 0; margin-bottom: 0; border-bottom: 1px solid var(--rule); cursor: pointer; border-left: 3px solid transparent; transition: border-left-color 0.15s; background: var(--paper); }'
if old_acard in html:
    html = html.replace(old_acard, new_acard)
    results.append('article-card paper: OK')
else:
    results.append('article-card: NOT FOUND')

# featured-card: same
old_fcard = '.featured-card { background: #ffffff;'
new_fcard = '.featured-card { background: var(--paper);'
if old_fcard in html:
    html = html.replace(old_fcard, new_fcard)
    results.append('featured-card paper: OK')
else:
    results.append('featured-card: NOT FOUND')

# sidebar: remove explicit white
old_sidebar = '.sidebar { padding: 16px; border-left: 1px solid var(--rule); position: sticky; top: 225px; height: calc(100vh - 225px); overflow-y: auto; align-self: start; background: #ffffff; }'
new_sidebar = '.sidebar { padding: 16px; border-left: 1px solid var(--rule); position: sticky; top: 225px; height: calc(100vh - 225px); overflow-y: auto; align-self: start; background: var(--paper); }'
if old_sidebar in html:
    html = html.replace(old_sidebar, new_sidebar)
    results.append('sidebar paper: OK')
else:
    results.append('sidebar: NOT FOUND')

# main-layout: remove white
old_ml = '.main-layout { display: grid; grid-template-columns: 1fr 260px; min-height: calc(100vh - 120px); background: #ffffff; }'
new_ml = '.main-layout { display: grid; grid-template-columns: 1fr 260px; min-height: calc(100vh - 120px); background: var(--paper); }'
if old_ml in html:
    html = html.replace(old_ml, new_ml)
    results.append('main-layout paper: OK')
else:
    results.append('main-layout: NOT FOUND')

# 4. Filter dropdowns — match content zone (var(--paper)) not white
old_sel = 'border: 1px solid rgba(0,0,0,0.25); background: #ffffff; color: var(--ink-2);'
new_sel = 'border: 1px solid rgba(0,0,0,0.25); background: var(--paper); color: var(--ink-2);'
if old_sel in html:
    html = html.replace(old_sel, new_sel)
    results.append('filter selects paper: OK')
else:
    results.append('filter selects: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
