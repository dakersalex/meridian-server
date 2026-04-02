import sqlite3, json

conn = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')
conn.row_factory = sqlite3.Row

# Find FA articles with short bodies — likely still AI summaries
# Real articles are 5000+ chars; AI summaries top out ~3000
rows = conn.execute("""
    SELECT id, title, url, LENGTH(body) as body_len, body
    FROM articles
    WHERE source = 'Foreign Affairs'
      AND url != ''
      AND LENGTH(body) < 4000
    ORDER BY LENGTH(body) ASC
""").fetchall()

out = []
for r in rows:
    body_preview = (r['body'] or '')[:200]
    # Heuristic: AI summaries start with prose like "The article...", "This article..."
    # Real text starts with bylines, pull quotes, actual prose
    looks_like_ai = any(body_preview.lower().startswith(p) for p in [
        'the article', 'this article', 'critiques', 'examines', 'argues that',
        'analyzes', 'discusses', 'explores', 'assesses', 'contends'
    ])
    out.append({
        'title': r['title'],
        'url': r['url'],
        'body_len': r['body_len'],
        'looks_like_ai': looks_like_ai,
        'preview': body_preview
    })

with open('/Users/alexdakers/meridian-server/tmp_fa_short.txt', 'w') as f:
    f.write(json.dumps(out, indent=2))
print(f"Found {len(out)} short FA articles")
