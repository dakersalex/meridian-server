import sqlite3

db = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')
c = db.cursor()

# Store Apr 18 as the last scored edition (the one we successfully scored today)
c.execute("INSERT OR REPLACE INTO kt_meta (key,value) VALUES (?,?)",
    ("eco_weekly_last_edition", "https://www.economist.com/weeklyedition/2026-04-18"))

# Ensure gate key for Apr 18 is set (it should be, but just in case)
from datetime import datetime
c.execute("INSERT OR REPLACE INTO kt_meta (key,value) VALUES (?,?)",
    ("ai_pick_economist_weekly_2026-04-18", datetime.now().isoformat()))

# Ensure gate key for Apr 11 is also set (scored in previous run even though post-processing failed)
c.execute("INSERT OR REPLACE INTO kt_meta (key,value) VALUES (?,?)",
    ("ai_pick_economist_weekly_2026-04-11", datetime.now().isoformat()))

db.commit()
db.close()
print("Gate keys and last_edition set")
