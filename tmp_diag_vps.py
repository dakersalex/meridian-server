import sqlite3

db = sqlite3.connect('/opt/meridian-server/meridian.db')

# Images on VPS
img_count = db.execute("SELECT COUNT(*) FROM article_images").fetchone()[0]
img_with_insight = db.execute("SELECT COUNT(*) FROM article_images WHERE insight != '' AND insight IS NOT NULL").fetchone()[0]
print(f"VPS images: {img_count} total, {img_with_insight} with insight")

# Sample image article IDs
sample = db.execute("SELECT article_id, insight FROM article_images WHERE insight != '' LIMIT 3").fetchall()
for r in sample:
    print(f"  article_id={r[0]}, insight={r[1][:80]}")

# Themes on VPS
theme_count = db.execute("SELECT COUNT(*) FROM kt_themes").fetchone()[0]
print(f"VPS themes: {theme_count}")

# Sample article IDs in kt_article_tags
try:
    tag_count = db.execute("SELECT COUNT(*) FROM kt_article_tags").fetchone()[0]
    sample_tags = db.execute("SELECT article_id, theme_name FROM kt_article_tags LIMIT 5").fetchall()
    print(f"VPS tagged articles: {tag_count}")
    for r in sample_tags:
        print(f"  {r[0]} -> {r[1]}")
except Exception as e:
    print(f"kt_article_tags error: {e}")
