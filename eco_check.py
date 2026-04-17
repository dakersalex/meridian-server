import sqlite3

db = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')
c = db.cursor()

# Clear gate keys for last 2 editions so they get rescored
c.execute("DELETE FROM kt_meta WHERE key LIKE 'ai_pick_economist_weekly_%'")
deleted = c.rowcount
db.commit()
db.close()
print(f"Cleared {deleted} economist weekly gate keys")
