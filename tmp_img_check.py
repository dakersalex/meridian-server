import sqlite3
db = sqlite3.connect('/opt/meridian-server/meridian.db')
total = db.execute("SELECT COUNT(*) FROM article_images").fetchone()[0]
arts = db.execute("SELECT COUNT(DISTINCT article_id) FROM article_images").fetchone()[0]
print(f"total images: {total}, articles with images: {arts}")

# Check how many of the 79 Iran brief articles have images
# Get article IDs that would be in the brief context
rows = db.execute("""
    SELECT a.id, a.title, COUNT(ai.id) as img_count
    FROM articles a
    LEFT JOIN article_images ai ON ai.article_id = a.id
    WHERE a.source = 'The Economist'
    AND a.status = 'full_text'
    GROUP BY a.id
    ORDER BY img_count DESC
    LIMIT 20
""").fetchall()
print("Economist full_text articles with image counts:")
for r in rows:
    print(f"  {r[2]} imgs: {r[1][:55]}")
