import sqlite3
db = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')
c = db.cursor()
c.execute("DELETE FROM kt_meta WHERE key LIKE 'ai_pick_economist_weekly_%'")
print(f"Cleared {c.rowcount} gate keys")
db.commit()
db.close()
