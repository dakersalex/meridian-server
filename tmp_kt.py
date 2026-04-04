import sqlite3, json

db = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')
c = db.cursor()

themes = c.execute("SELECT id, label, article_count, is_gold FROM kt_themes ORDER BY article_count DESC").fetchall()
meta = c.execute("SELECT * FROM kt_meta").fetchall()

print(json.dumps({
    'themes': [{'id': r[0], 'label': r[1], 'count': r[2], 'gold': r[3]} for r in themes],
    'meta': meta
}))
