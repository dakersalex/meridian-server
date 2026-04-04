import sqlite3, json

db = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')
c = db.cursor()

# Check schema
schema = c.execute("SELECT sql FROM sqlite_master WHERE name='kt_themes'").fetchone()
themes_raw = c.execute("SELECT * FROM kt_themes LIMIT 15").fetchall()
cols = [d[0] for d in c.description]

print(json.dumps({'schema': schema[0] if schema else None, 'cols': cols, 'sample': themes_raw[:5]}))
