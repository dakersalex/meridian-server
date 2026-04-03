
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# The broken line — missing semicolons before return
old = "textContent='meridianreader.com · connected'return true;}}catch(e){}"
new = "textContent='meridianreader.com · connected';return true;}}catch(e){}"
if old in html:
    html = html.replace(old, new)
    results.append('connected return: OK')
else:
    results.append('connected return: NOT FOUND')

old2 = "textContent='Server offline — check systemctl status meridian on VPS'return false;"
new2 = "textContent='Server offline — check systemctl status meridian on VPS';return false;"
if old2 in html:
    html = html.replace(old2, new2)
    results.append('offline return: OK')
else:
    results.append('offline return: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
