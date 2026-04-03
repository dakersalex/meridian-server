with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    src = f.read()

# Fix 1: score_and_autosave_new_articles — restrict to core sources only
OLD1 = '''        rows = cx.execute("""
            SELECT id, source, url, title, topic, tags
            FROM articles
            WHERE source IN ('Financial Times', 'The Economist')
              AND auto_saved = 0
              AND status NOT IN ('agent')
              AND saved_at >= ?
              AND title != ''
        """, (cutoff_ts,)).fetchall()'''

NEW1 = '''        rows = cx.execute("""
            SELECT id, source, url, title, topic, tags
            FROM articles
            WHERE source IN ('Financial Times', 'The Economist')
              AND auto_saved = 0
              AND status NOT IN ('agent')
              AND saved_at >= ?
              AND title != ''
        """, (cutoff_ts,)).fetchall()
        # Note: only FT/Economist scored here — FA/Bloomberg arrive via scraper/extension
        # Non-core sources (CNN, CFR, FP etc) are never auto-saved to Feed, only Suggested'''

# Fix 2: run_agent — only auto-save to Feed from core sources
# run_agent picks from suggested_articles scored >=8 and saves to articles table
# Add source filter so only FT/Economist/FA/Bloomberg go to Feed
OLD2 = '''def run_agent():
    """Auto-save high-scoring suggested articles to Feed."""
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        candidates = cx.execute(
            "SELECT * FROM suggested_articles WHERE status='new' AND score >= 8"
        ).fetchall()'''

NEW2 = '''# Core sources allowed in the main Feed via auto-save
FEED_CORE_SOURCES = {'Financial Times', 'The Economist', 'Foreign Affairs', 'Bloomberg'}

def run_agent():
    """Auto-save high-scoring suggested articles to Feed.
    Only FT/Economist/FA/Bloomberg go to Feed — all other sources stay in Suggested."""
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        candidates = cx.execute(
            "SELECT * FROM suggested_articles WHERE status='new' AND score >= 8"
        ).fetchall()'''

# Fix 3: in run_agent body, add source check before saving to Feed
OLD3 = '''        art = {
            "id": aid, "source": row["source"], "url": row["url"],
            "title": row["title"], "body": "", "summary": row.get("reason", ""),
            "topic": "", "tags": "[]", "saved_at": now_ts(), "fetched_at": None,
            "status": "agent", "pub_date": row.get("pub_date", ""), "auto_saved": 1,
        }
        upsert_article(art)
        with sqlite3.connect(DB_PATH) as cx:
            cx.execute("UPDATE suggested_articles SET status='saved' WHERE id=?", (row["id"],))'''

NEW3 = '''        # Non-core sources stay in Suggested — only core sources go to Feed
        if row["source"] not in FEED_CORE_SOURCES:
            log.info(f"Agent: '{row['title'][:50]}' from '{row['source']}' — non-core, keeping in Suggested only")
            continue

        art = {
            "id": aid, "source": row["source"], "url": row["url"],
            "title": row["title"], "body": "", "summary": row.get("reason", ""),
            "topic": "", "tags": "[]", "saved_at": now_ts(), "fetched_at": None,
            "status": "agent", "pub_date": row.get("pub_date", ""), "auto_saved": 1,
        }
        upsert_article(art)
        with sqlite3.connect(DB_PATH) as cx:
            cx.execute("UPDATE suggested_articles SET status='saved' WHERE id=?", (row["id"],))'''

results = []
for old, new, label in [(OLD1, NEW1, "score_and_autosave comment"), (OLD2, NEW2, "run_agent FEED_CORE_SOURCES"), (OLD3, NEW3, "run_agent source filter")]:
    if old in src:
        src = src.replace(old, new)
        results.append(f"OK: {label}")
    else:
        results.append(f"FAILED: {label}")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(src)

for r in results:
    print(r)
