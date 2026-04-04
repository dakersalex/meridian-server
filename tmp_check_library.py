
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# ── 1. Remove LIBRARY text node (leftover from dedup)
# It appears as bare text before the main-layout div
old_library = '\n<!-- KEY THEMES VIEW -->'
# Actually check what it looks like exactly
if 'LIBRARY' in html:
    # Find it
    idx = html.find('LIBRARY')
    context = html[idx-50:idx+50]
    results.append(f'LIBRARY context: {repr(context)}')
else:
    results.append('No LIBRARY text found')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
