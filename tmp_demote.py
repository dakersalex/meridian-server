import sqlite3

DB = '/Users/alexdakers/meridian-server/meridian.db'
conn = sqlite3.connect(DB)

rows = conn.execute("""
    SELECT id, source, title FROM articles
    WHERE auto_saved=1 AND source NOT IN ('Financial Times','The Economist','Foreign Affairs','Bloomberg')
    ORDER BY source
""").fetchall()

conn.execute("""
    UPDATE articles SET auto_saved=0
    WHERE auto_saved=1
    AND source NOT IN ('Financial Times','The Economist','Foreign Affairs','Bloomberg')
""")
conn.commit()

remaining = conn.execute("SELECT COUNT(*) FROM articles WHERE auto_saved=1").fetchone()[0]
by_src = conn.execute("SELECT source, COUNT(*) FROM articles WHERE auto_saved=1 GROUP BY source ORDER BY COUNT(*) DESC").fetchall()

with open('/Users/alexdakers/meridian-server/tmp_demote_result.txt', 'w') as f:
    f.write(f"Demoted {len(rows)} non-core articles from auto_saved=1 to auto_saved=0:\n")
    for r in rows:
        f.write(f"  [{r[1]}] {r[2][:70]}\n")
    f.write(f"\nRemaining auto_saved=1: {remaining}\n")
    for src, cnt in by_src:
        f.write(f"  {src}: {cnt}\n")
conn.close()
print("DONE")
