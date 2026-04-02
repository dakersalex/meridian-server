import sqlite3, json

c = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')

tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

sources = dict(c.execute("SELECT source, COUNT(*) FROM articles GROUP BY source").fetchall())
total = sum(sources.values())

# KT state (may not exist on Mac)
if 'key_themes' in tables:
    themes_count = c.execute("SELECT COUNT(*) FROM key_themes").fetchone()[0]
    tagged = c.execute("SELECT COUNT(*) FROM articles WHERE theme_id IS NOT NULL").fetchone()[0]
    themes_with_kf = c.execute("SELECT COUNT(*) FROM key_themes WHERE key_facts != '[]' AND key_facts IS NOT NULL AND key_facts != ''").fetchone()[0]
    theme_rows = c.execute("SELECT name, key_facts FROM key_themes ORDER BY id").fetchall()
    themes = [{"name": n, "has_kf": bool(kf and kf != '[]' and kf != '')} for n, kf in theme_rows]
else:
    themes_count = tagged = themes_with_kf = 0
    themes = []

# Image state
if 'article_images' in tables:
    imgs = c.execute("SELECT COUNT(*) FROM article_images").fetchone()[0]
    arts_with_imgs = c.execute("SELECT COUNT(*) FROM articles WHERE id IN (SELECT DISTINCT article_id FROM article_images)").fetchone()[0]
else:
    imgs = arts_with_imgs = 0

result = {
    "tables": tables,
    "total": total,
    "by_source": sources,
    "kt_themes": themes_count,
    "kt_tagged": tagged,
    "kt_with_kf": themes_with_kf,
    "images": imgs,
    "arts_with_imgs": arts_with_imgs,
    "themes": themes
}

with open('/tmp/hc_result.txt', 'w') as f:
    f.write(json.dumps(result, indent=2))
print("HC_DONE")
