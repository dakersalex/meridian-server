"""Delete the 87 legacy article_images rows on VPS that have mac_id IS NULL.
These are duplicates from a partial push before mac_id dedup was implemented."""
import sqlite3

db = sqlite3.connect("/opt/meridian-server/meridian.db")
before = db.execute("SELECT COUNT(*) FROM article_images").fetchone()[0]
db.execute("DELETE FROM article_images WHERE mac_id IS NULL")
db.commit()
after = db.execute("SELECT COUNT(*) FROM article_images").fetchone()[0]
print(f"Deleted {before - after} legacy rows. Remaining: {after}")
