"""
Diagnose chart selection for the Iran War brief.
Shows: all available images, their scores against each section, which were selected.
"""
import sqlite3, re

DB = "/opt/meridian-server/meridian.db"
db = sqlite3.connect(DB)

# Get Iran-tagged articles (theme articles used in brief)
# The brief used articles filtered by Iran/war/gulf keywords on the frontend
# Let's find Economist articles that have images and are plausibly Iran-related
iran_articles = db.execute("""
    SELECT a.id, a.title, a.source
    FROM articles a
    INNER JOIN article_images ai ON ai.article_id = a.id
    WHERE a.source = 'The Economist'
    AND (
        LOWER(a.title) LIKE '%iran%'
        OR LOWER(a.title) LIKE '%gulf%'
        OR LOWER(a.title) LIKE '%hormuz%'
        OR LOWER(a.title) LIKE '%oil%'
        OR LOWER(a.title) LIKE '%energy%'
        OR LOWER(a.title) LIKE '%war%'
        OR LOWER(a.title) LIKE '%middl%'
        OR LOWER(a.summary) LIKE '%iran%'
    )
    GROUP BY a.id
""").fetchall()

print(f"Iran-related Economist articles with images: {len(iran_articles)}")
for a in iran_articles:
    imgs = db.execute("SELECT id, caption, description, insight FROM article_images WHERE article_id=?", (a[0],)).fetchall()
    print(f"\n  Article: {a[1][:70]}")
    for img in imgs:
        print(f"    img_id={img[0]} caption={img[1][:40]}")
        print(f"      desc:    {img[2][:80]}")
        print(f"      insight: {img[3][:80]}")

# Also show total available images on VPS
total = db.execute("SELECT COUNT(*) FROM article_images WHERE insight != '' AND insight IS NOT NULL").fetchone()[0]
print(f"\nTotal VPS images with insight: {total}")

# Check for duplicate/near-duplicate insights (same chart appearing twice)
all_imgs = db.execute("SELECT id, article_id, description, insight FROM article_images WHERE insight != '' AND insight IS NOT NULL").fetchall()
print(f"\nChecking for near-duplicate insights (potential same chart twice):")
seen = {}
for img in all_imgs:
    key = img[3][:60].lower().strip()
    if key in seen:
        print(f"  DUPLICATE insight:")
        print(f"    img {seen[key]}: {img[3][:80]}")
        print(f"    img {img[0]}: {img[3][:80]}")
    else:
        seen[key] = img[0]

db.close()
