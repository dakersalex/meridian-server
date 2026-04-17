import sqlite3
from datetime import datetime

db = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')
c = db.cursor()

# Articles added today from Economist as auto_saved (AI picks)
c.execute("""
    SELECT title, pub_date, status, saved_at
    FROM articles
    WHERE source='The Economist' AND auto_saved=1
    AND DATE(datetime(saved_at/1000,'unixepoch','localtime')) = '2026-04-17'
    ORDER BY saved_at DESC
""")
rows = c.fetchall()

with open('/Users/alexdakers/meridian-server/logs/eco_picks_today.txt', 'w') as f:
    f.write(f"Economist AI picks added today: {len(rows)}\n\n")
    for r in rows:
        f.write(f"  [{r[2]}] {r[0][:70]}\n")

print(f"Economist AI picks today: {len(rows)}")
for r in rows:
    print(f"  {r[0][:60]}")
db.close()
