import sqlite3
db = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')
c = db.cursor()
c.execute("DELETE FROM kt_meta WHERE key='ai_pick_economist_weekly_2026-04-11'")
print(f"Cleared Apr 11 gate: {c.rowcount}")
# Also check current state
c.execute("SELECT key, value FROM kt_meta WHERE key LIKE 'ai_pick_economist_weekly_%'")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1][:30]}")
db.commit()
db.close()
