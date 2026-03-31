import sqlite3
db = sqlite3.connect('/opt/meridian-server/meridian.db')
total = db.execute("SELECT COUNT(*) FROM article_images").fetchone()[0]
with_insight = db.execute("SELECT COUNT(*) FROM article_images WHERE insight != '' AND insight IS NOT NULL").fetchone()[0]
print(f"VPS article_images: {total} total, {with_insight} with insight")
# Sample a few insights to confirm data is good
samples = db.execute("SELECT article_id, insight FROM article_images WHERE insight != '' LIMIT 3").fetchall()
for r in samples:
    print(f"  {r[0]}: {r[1][:80]}")
