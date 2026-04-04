import sqlite3, json

db = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')
c = db.cursor()

tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]

rows = c.execute("""
    SELECT source, COUNT(*) as total,
           SUM(CASE WHEN body IS NOT NULL AND length(body)>100 THEN 1 ELSE 0 END) as full_text
    FROM articles GROUP BY source ORDER BY total DESC
""").fetchall()

enriched = c.execute("SELECT COUNT(*) FROM articles WHERE summary IS NOT NULL").fetchone()[0]
title_only = c.execute("SELECT COUNT(*) FROM articles WHERE body IS NULL OR length(body)<100").fetchone()[0]
total = c.execute("SELECT COUNT(*) FROM articles").fetchone()[0]

# KT table name
kt_count = 0
kt_table = None
for t in tables:
    if 'theme' in t.lower() or 'kt' in t.lower():
        kt_table = t
        kt_count = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        break

result = {
    'tables': tables,
    'total': total,
    'enriched': enriched,
    'title_only': title_only,
    'by_source': [{'source': r[0], 'total': r[1], 'full_text': r[2]} for r in rows],
    'kt_table': kt_table,
    'kt_count': kt_count
}
print(json.dumps(result))
