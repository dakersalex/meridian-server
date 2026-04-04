
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# The info-strip outer div has flex-wrap:wrap — change to nowrap + overflow-x:auto
old_is_outer = 'display:none;align-items:flex-start;gap:0;padding:14px 24px;background:var(--paper);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:wrap;position:sticky;top:184px;z-index:51;isolation:isolate;'
new_is_outer = 'display:none;align-items:flex-start;gap:0;padding:14px 24px;background:var(--paper);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap;overflow-x:auto;position:sticky;top:184px;z-index:51;isolation:isolate;'
if old_is_outer in html:
    html = html.replace(old_is_outer, new_is_outer)
    results.append('info-strip nowrap: OK')
else:
    results.append('info-strip: NOT FOUND')

# Also fix the 24h activity pills — remove background and border, plain text only
old_24h_css = '.activity-pill { font-size: 11px; padding: 2px 8px; border-radius: 20px; white-space: nowrap; cursor: default; border: 0.5px solid rgba(0,0,0,0.1); }'
new_24h_css = '.activity-pill { font-size: 11px; padding: 1px 0; white-space: nowrap; cursor: default; background: none !important; border: none !important; border-radius: 0; }'
if old_24h_css in html:
    html = html.replace(old_24h_css, new_24h_css)
    results.append('activity-pill plain: OK')
else:
    # Try alternate
    old_24h_css2 = '.activity-pill { font-size: 11px; padding: 2px 8px; border-radius: 20px; white-space: nowrap; cursor: default; }'
    new_24h_css2 = '.activity-pill { font-size: 11px; padding: 1px 0; white-space: nowrap; cursor: default; background: none !important; border: none !important; border-radius: 0; }'
    if old_24h_css2 in html:
        html = html.replace(old_24h_css2, new_24h_css2)
        results.append('activity-pill plain (v2): OK')
    else:
        results.append('activity-pill: NOT FOUND')

old_pill_zero = '.activity-pill-zero { background: var(--paper-2); color: var(--ink-3); }'
new_pill_zero = '.activity-pill-zero { color: var(--ink-3); }'
if old_pill_zero in html:
    html = html.replace(old_pill_zero, new_pill_zero)
    results.append('pill-zero plain: OK')
else:
    results.append('pill-zero: NOT FOUND')

old_pill_active = '.activity-pill-active { background: var(--green-bg); color: var(--green); border-color: rgba(45,107,69,0.25); }'
new_pill_active = '.activity-pill-active { color: var(--green); font-weight: 500; }'
if old_pill_active in html:
    html = html.replace(old_pill_active, new_pill_active)
    results.append('pill-active plain: OK')
else:
    results.append('pill-active: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
