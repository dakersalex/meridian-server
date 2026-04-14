import sqlite3
db = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')
c = db.cursor()
c.execute("SELECT key, value FROM kt_meta WHERE key LIKE 'last_sync%' OR key LIKE 'ai_pick_last%'")
for row in c.fetchall():
    print(row)
