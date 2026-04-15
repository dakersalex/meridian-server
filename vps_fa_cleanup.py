import sqlite3
db = sqlite3.connect('/opt/meridian-server/meridian.db')
c = db.cursor()
c.execute("DELETE FROM articles WHERE source='Foreign Affairs' AND url LIKE '%/book-reviews/%'")
c.execute("UPDATE articles SET pub_date='2026-03-03' WHERE id='cde9fc4c99b7929e'")
db.commit()
print(f"deleted: {c.rowcount}")
db.close()
