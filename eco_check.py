import sqlite3
db = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')
c = db.cursor()
c.execute("DELETE FROM kt_meta WHERE key='ai_pick_economist_weekly_2026-04-11'")
print(f"Cleared: {c.rowcount}")
db.commit()
db.close()
