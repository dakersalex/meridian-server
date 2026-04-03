
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# ── 1. Activity pills — change active from amber to green (same as live data signal)
old_pill_active = '.activity-pill-active { background: #f5ede4; color: var(--accent); border-color: #e8c9a8; }'
new_pill_active = '.activity-pill-active { background: var(--green-bg); color: var(--green); border-color: rgba(45,107,69,0.25); }'
if old_pill_active in html:
    html = html.replace(old_pill_active, new_pill_active)
    results.append('activity-pill-active green: OK')
else:
    results.append('activity-pill-active: NOT FOUND')

# ── 2. Card area background — feed-area already set to #ffffff
# The issue is the featured-card and article-card themselves still use var(--paper-2) / var(--paper)
# Change featured-card to white
old_feat_bg = '.featured-card { background: var(--paper-2); border: none; border-bottom: 1px solid var(--rule); padding: 0; margin-bottom: 2px; cursor: pointer; border-left: 3px solid transparent; transition: border-left-color 0.15s; }'
new_feat_bg = '.featured-card { background: #ffffff; border: none; border-bottom: 1px solid var(--rule); padding: 0; margin-bottom: 2px; cursor: pointer; border-left: 3px solid transparent; transition: border-left-color 0.15s; }'
if old_feat_bg in html:
    html = html.replace(old_feat_bg, new_feat_bg)
    results.append('featured-card white: OK')
else:
    results.append('featured-card bg: NOT FOUND')

# ── 3. Body background — set to a slightly darker paper so the white cards pop
# Currently body background is var(--paper) = #faf8f4 same as headers
# Cards are white but body fills the gaps — needs to be the same warm cream as headers
# so the white card area stands out. Body is already correct — the issue is the
# main-layout background bleeds through. Set main-layout to white.
old_main_layout = '.main-layout { display: grid; grid-template-columns: 1fr 260px; min-height: calc(100vh - 120px); }'
new_main_layout = '.main-layout { display: grid; grid-template-columns: 1fr 260px; min-height: calc(100vh - 120px); background: #ffffff; }'
if old_main_layout in html:
    html = html.replace(old_main_layout, new_main_layout)
    results.append('main-layout white: OK')
else:
    results.append('main-layout: NOT FOUND')

# ── 4. Info-strip background — explicitly set to var(--paper) so it matches headers
# and NOT white, keeping the visual separation
old_info_style = 'display:flex;align-items:center;gap:10px;padding:6px 20px;background:var(--paper-2);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap;position:sticky;top:147px;z-index:52;isolation:isolate;'
new_info_style = 'display:flex;align-items:center;gap:10px;padding:6px 20px;background:var(--paper);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap;position:sticky;top:147px;z-index:52;isolation:isolate;'
if old_info_style in html:
    html = html.replace(old_info_style, new_info_style)
    results.append('info-strip paper bg: OK')
else:
    results.append('info-strip: NOT FOUND')

# ── 5. Sidebar background explicitly white
old_sidebar = '.sidebar { padding: 16px; border-left: 1px solid var(--rule); position: sticky; top: 225px; height: calc(100vh - 225px); overflow-y: auto; align-self: start; }'
new_sidebar = '.sidebar { padding: 16px; border-left: 1px solid var(--rule); position: sticky; top: 225px; height: calc(100vh - 225px); overflow-y: auto; align-self: start; background: #ffffff; }'
if old_sidebar in html:
    html = html.replace(old_sidebar, new_sidebar)
    results.append('sidebar white: OK')
else:
    results.append('sidebar: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
