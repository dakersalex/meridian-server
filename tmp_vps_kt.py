import sqlite3, json, sys

db = sqlite3.connect('/opt/meridian-server/meridian.db')
c = db.cursor()
themes = c.execute('SELECT name, article_count, last_updated FROM kt_themes ORDER BY article_count DESC').fetchall()
total = c.execute('SELECT COUNT(*) FROM articles').fetchone()[0]
fa = c.execute("SELECT COUNT(*), SUM(CASE WHEN body IS NOT NULL AND length(body)>100 THEN 1 ELSE 0 END) FROM articles WHERE source='Foreign Affairs'").fetchone()
print(json.dumps({'total': total, 'fa_total': fa[0], 'fa_full': fa[1], 'themes': [{'name': r[0], 'count': r[1]} for r in themes]}))
