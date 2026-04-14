import sqlite3

db = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')
c = db.cursor()

# Preview before delete
c.execute("SELECT id, title, url FROM articles WHERE source='Foreign Affairs' AND url LIKE '%/book-reviews/%'")
rows = c.fetchall()
print(f"Found {len(rows)} book-review stubs:")
for r in rows:
    print(f"  {r[1]} | {r[2]}")

# Delete them
c.execute("DELETE FROM articles WHERE source='Foreign Affairs' AND url LIKE '%/book-reviews/%'")
print(f"Deleted {c.rowcount} rows")
db.commit()
db.close()
