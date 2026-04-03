
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

old = '''.kt-fact-top {
  background: var(--paper-2);
  padding: 4px 12px 6px;
  border-bottom: 1px solid var(--rule);
  height: 68px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 1px;
  overflow: hidden;
}'''

new = '''.kt-fact-top {
  background: var(--paper-2);
  padding: 2px 12px 6px;
  border-bottom: 1px solid var(--rule);
  height: 68px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 1px;
  overflow: hidden;
}'''

if old in html:
    html = html.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print('PATCHED OK')
else:
    print('NOT FOUND')
