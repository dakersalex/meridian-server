import sqlite3
db = sqlite3.connect("/opt/meridian-server/meridian.db")
r = db.execute("DELETE FROM articles WHERE source='The Economist'")
db.commit()
print(f"{r.rowcount} Economist articles deleted from VPS")
db.close()
