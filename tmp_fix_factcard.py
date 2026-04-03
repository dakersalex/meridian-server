
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

old = '''.kt-fact-top {
  background: var(--paper-2);
  padding: 10px 12px;
  border-bottom: 1px solid var(--rule);
  height: 68px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}'''

new = '''.kt-fact-top {
  background: var(--paper-2);
  padding: 10px 12px;
  border-bottom: 1px solid var(--rule);
  min-height: 68px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}'''

if old in html:
    html = html.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print('PATCHED OK')
else:
    print('NOT FOUND — no change made')
