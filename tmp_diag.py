import sqlite3

db = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')

# Check kt_themes schema
cols = db.execute("PRAGMA table_info(kt_themes)").fetchall()
print("kt_themes cols:", [c[1] for c in cols])

# All theme names
themes = db.execute("SELECT * FROM kt_themes LIMIT 20").fetchall()
print("Themes:", themes)

# Check kt_article_tags schema
cols2 = db.execute("PRAGMA table_info(kt_article_tags)").fetchall()
print("kt_article_tags cols:", [c[1] for c in cols2])

# Articles with images - sample article IDs
sample_img_ids = db.execute("SELECT article_id FROM article_images LIMIT 5").fetchall()
print("Sample image article_ids:", sample_img_ids)

# Sample article IDs from articles table (Economist)
sample_art_ids = db.execute("SELECT id FROM articles WHERE source='The Economist' LIMIT 5").fetchall()
print("Sample Economist article IDs:", sample_art_ids)
