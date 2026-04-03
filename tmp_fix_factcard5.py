
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

old = '''.kt-fact-title {
  font-size: 12px;
  font-weight: 500;
  line-height: 1.3;
  color: var(--ink);
  margin-top: auto;
}'''

new = '''.kt-fact-title {
  font-size: 12px;
  font-weight: 500;
  line-height: 1.3;
  color: var(--ink);
}'''

if old in html:
    html = html.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print('PATCHED OK')
else:
    print('NOT FOUND')
