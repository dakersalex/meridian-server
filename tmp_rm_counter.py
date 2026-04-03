
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

old = '<div id="feed-counter" style="font-size:11px;color:var(--ink-3);padding:12px 0 8px;border-bottom:1px solid var(--rule);margin-bottom:12px;"></div>'
new = '<div id="feed-counter" style="display:none"></div>'

if old in html:
    html = html.replace(old, new)
    print('OK')
else:
    print('NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)
