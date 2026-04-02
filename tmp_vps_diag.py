import sqlite3, json

c = sqlite3.connect('/opt/meridian-server/meridian.db')

# Find the latest timestamp
latest_ts = c.execute("SELECT MAX(last_updated) FROM kt_themes").fetchone()[0]

# Preview what we'll delete
to_delete = c.execute("SELECT name, last_updated FROM kt_themes WHERE last_updated < ?", (latest_ts,)).fetchall()
print(f"Deleting {len(to_delete)} stale themes:")
for name, ts in to_delete:
    print(f"  - {name} (ts={ts})")

# Delete stale rows and their tag assignments
stale_names = [r[0] for r in to_delete]
for name in stale_names:
    c.execute("DELETE FROM article_theme_tags WHERE theme_name=?", (name,))
    c.execute("DELETE FROM kt_themes WHERE name=?", (name,))

c.commit()

remaining = c.execute("SELECT name, article_count FROM kt_themes ORDER BY article_count DESC").fetchall()
print(f"\nRemaining {len(remaining)} themes:")
for name, ac in remaining:
    print(f"  {ac:4d} articles — {name}")
