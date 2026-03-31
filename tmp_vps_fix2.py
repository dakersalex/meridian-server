import sqlite3
db = sqlite3.connect('/opt/meridian-server/meridian.db')
# init_db creates this if missing — just create it directly
db.execute("""CREATE TABLE IF NOT EXISTS kt_article_tags (
    article_id TEXT NOT NULL,
    theme_name TEXT NOT NULL,
    relevance_score REAL DEFAULT 0,
    tagged_at INTEGER NOT NULL,
    PRIMARY KEY (article_id, theme_name)
)""")
db.commit()
count = db.execute("SELECT COUNT(*) FROM kt_article_tags").fetchone()[0]
print(f"kt_article_tags OK, rows: {count}")
