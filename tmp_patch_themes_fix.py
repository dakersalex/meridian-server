with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    src = f.read()

# Add null guard: filter out any themes missing name or keywords before processing
OLD = '''  // Build combined theme list: AI themes sorted by article_count desc, then manual slots
  const aiThemes = [...ktThemes].sort((a, b) => (b.article_count || 0) - (a.article_count || 0));'''

NEW = '''  // Build combined theme list: AI themes sorted by article_count desc, then manual slots
  // Guard against any malformed theme rows (missing name/keywords from partial seeds)
  const aiThemes = [...ktThemes]
    .filter(t => t && t.name && t.keywords)
    .sort((a, b) => (b.article_count || 0) - (a.article_count || 0));'''

results = []
if OLD in src:
    src = src.replace(OLD, NEW)
    results.append("null guard: OK")
else:
    results.append("null guard: FAILED")

with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(src)

for r in results:
    print(r)
