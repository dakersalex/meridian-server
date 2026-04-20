#!/usr/bin/env python3
"""
Session 62 patch: unfetchable article exclusion
1. Fix health_daily and health_enrichment to exclude unfetchable
2. Create unfetchable_urls blocklist table in init_db
3. Seed blocklist with 9 existing unfetchable URLs
4. Update update_article PATCH handler to populate blocklist + demote from feed/suggested
5. Patch rss_ai_pick.py to filter Alphaville/Economist-indicators/blocklisted URLs
"""
import ast
import pathlib
import sqlite3
import sys

BASE = pathlib.Path(__file__).parent
SERVER = BASE / "server.py"
RSS = BASE / "rss_ai_pick.py"
DB = BASE / "meridian.db"

# ─── 1 + 2 + 4: server.py edits ─────────────────────────────────────────────
src = SERVER.read_text()

# --- Edit 1a: health_daily unenriched count excludes unfetchable ---
old_1a = '        # Unenriched count\n        unenriched = cx.execute("SELECT COUNT(*) FROM articles WHERE summary IS NULL OR summary=\'\'").fetchone()[0]'
new_1a = '        # Unenriched count — exclude unfetchable (they structurally cannot be enriched)\n        unenriched = cx.execute("SELECT COUNT(*) FROM articles WHERE (summary IS NULL OR summary=\'\') AND (status IS NULL OR status != \'unfetchable\')").fetchone()[0]'
assert src.count(old_1a) == 1, f"edit 1a not found (count={src.count(old_1a)})"
src = src.replace(old_1a, new_1a)

# --- Edit 1b: health_enrichment unenriched count excludes unfetchable ---
old_1b = '''        # Count unenriched
        unenriched = cx.execute(
            "SELECT source, COUNT(*) as cnt FROM articles WHERE (summary IS NULL OR summary=\'\') GROUP BY source"
        ).fetchall()'''
new_1b = '''        # Count unenriched — exclude unfetchable (they structurally cannot be enriched)
        unenriched = cx.execute(
            "SELECT source, COUNT(*) as cnt FROM articles WHERE (summary IS NULL OR summary=\'\') AND (status IS NULL OR status != \'unfetchable\') GROUP BY source"
        ).fetchall()'''
assert src.count(old_1b) == 1, f"edit 1b not found (count={src.count(old_1b)})"
src = src.replace(old_1b, new_1b)

# --- Edit 2: add unfetchable_urls table creation in init_db ---
# Insert right after kt_meta table creation
old_2 = """        cx.execute('CREATE TABLE IF NOT EXISTS kt_meta '
                   '(key TEXT PRIMARY KEY, value TEXT NOT NULL)')"""
new_2 = """        cx.execute('CREATE TABLE IF NOT EXISTS kt_meta '
                   '(key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        # Unfetchable URL blocklist — URLs that produced no body (FT Alphaville,
        # FT Professional, Bloomberg, Eco indicators). Prevents RSS pick from re-suggesting them.
        cx.execute('CREATE TABLE IF NOT EXISTS unfetchable_urls '
                   '(url TEXT PRIMARY KEY, source TEXT, reason TEXT DEFAULT \"\", added_at INTEGER NOT NULL)')"""
assert src.count(old_2) == 1, f"edit 2 not found (count={src.count(old_2)})"
src = src.replace(old_2, new_2)

# --- Edit 4: update_article PATCH handler — populate blocklist + demote ---
old_4 = '''@app.route("/api/articles/<aid>", methods=["PATCH"])
def update_article(aid):
    body = request.json or {}
    cx = sqlite3.connect(DB_PATH)
    for key in ["body", "summary", "topic", "tags", "status", "pub_date"]:
        if key in body:
            cx.execute(f"UPDATE articles SET {key}=? WHERE id=?", (body[key], aid))
    cx.commit()
    cx.close()
    return jsonify({"ok": True})'''
new_4 = '''@app.route("/api/articles/<aid>", methods=["PATCH"])
def update_article(aid):
    body = request.json or {}
    cx = sqlite3.connect(DB_PATH)
    for key in ["body", "summary", "topic", "tags", "status", "pub_date"]:
        if key in body:
            cx.execute(f"UPDATE articles SET {key}=? WHERE id=?", (body[key], aid))
    # If status set to unfetchable: add URL to blocklist, demote from feed, remove from suggested
    if body.get("status") == "unfetchable":
        row = cx.execute("SELECT url, source FROM articles WHERE id=?", (aid,)).fetchone()
        if row and row[0]:
            url, source = row[0], row[1] or ""
            cx.execute(
                "INSERT OR IGNORE INTO unfetchable_urls (url, source, reason, added_at) VALUES (?,?,?,?)",
                (url, source, "marked unfetchable by extension body-fetcher", now_ts())
            )
            cx.execute("UPDATE articles SET auto_saved=0 WHERE id=?", (aid,))
            cx.execute("DELETE FROM suggested_articles WHERE url=?", (url,))
            log.info(f"Unfetchable: blocklisted {url} and demoted from feed/suggested")
    cx.commit()
    cx.close()
    return jsonify({"ok": True})'''
assert src.count(old_4) == 1, f"edit 4 not found (count={src.count(old_4)})"
src = src.replace(old_4, new_4)

# Syntax check before writing
try:
    ast.parse(src)
except SyntaxError as e:
    print(f"SYNTAX ERROR in patched server.py: {e}")
    sys.exit(1)

SERVER.write_text(src)
print(f"server.py: 4 edits applied, ast.parse OK, {len(src)} chars")

# ─── 5: rss_ai_pick.py edits ────────────────────────────────────────────────
rss_src = RSS.read_text()

# --- Edit 5a: add Alphaville RSS fetch + blocklist function ---
# Insert helper function right before def rss_ai_pick():
old_5a = "def rss_ai_pick():\n    \"\"\"Main RSS-based AI pick function.\"\"\""
new_5a = '''def fetch_unfetchable_blocklist():
    """Return set of URLs to skip: FT Alphaville URLs + DB unfetchable_urls table."""
    blocked = set()
    # 1. Fetch Alphaville RSS and collect its URLs (Alphaville is FT Professional only)
    try:
        alpha_articles = fetch_rss("https://www.ft.com/alphaville?format=rss")
        for a in alpha_articles:
            if a.get("url"):
                blocked.add(a["url"])
        log.info(f"RSS pick: blocklisted {len(blocked)} Alphaville URLs")
    except Exception as e:
        log.warning(f"RSS pick: Alphaville blocklist fetch failed: {e}")
    # 2. Pull from DB unfetchable_urls table
    try:
        with sqlite3.connect(str(DB_PATH)) as cx:
            cx.execute("CREATE TABLE IF NOT EXISTS unfetchable_urls "
                       "(url TEXT PRIMARY KEY, source TEXT, reason TEXT DEFAULT '', added_at INTEGER NOT NULL)")
            db_blocked = set(r[0] for r in cx.execute("SELECT url FROM unfetchable_urls").fetchall())
        blocked.update(db_blocked)
        log.info(f"RSS pick: blocklisted {len(db_blocked)} URLs from unfetchable_urls table")
    except Exception as e:
        log.warning(f"RSS pick: DB blocklist fetch failed: {e}")
    return blocked


def is_pattern_unfetchable(url, source):
    """Pattern-based rejection for known-unfetchable URL shapes."""
    # Economist data pages are not articles
    if "/economic-and-financial-indicators/" in url:
        return True
    # Bloomberg is manual-clip only (RSS pick must never auto-save Bloomberg)
    if source == "Bloomberg" or "bloomberg.com" in url:
        return True
    return False


def rss_ai_pick():
    """Main RSS-based AI pick function."""'''
assert rss_src.count(old_5a) == 1, f"edit 5a not found (count={rss_src.count(old_5a)})"
rss_src = rss_src.replace(old_5a, new_5a)

# --- Edit 5b: call blocklist in candidate loop ---
old_5b = '''    # Build known URLs
    with sqlite3.connect(str(DB_PATH)) as cx:
        all_urls = set(r[0] for r in cx.execute("SELECT url FROM articles WHERE url!=\'\'").fetchall())
        suggested_urls = set(r[0] for r in cx.execute("SELECT url FROM suggested_articles WHERE url!=\'\'").fetchall())
    known = all_urls | suggested_urls'''
new_5b = '''    # Build known URLs
    with sqlite3.connect(str(DB_PATH)) as cx:
        all_urls = set(r[0] for r in cx.execute("SELECT url FROM articles WHERE url!=\'\'").fetchall())
        suggested_urls = set(r[0] for r in cx.execute("SELECT url FROM suggested_articles WHERE url!=\'\'").fetchall())
    known = all_urls | suggested_urls
    # Unfetchable blocklist: Alphaville URLs (live fetched) + DB unfetchable_urls + pattern matches
    blocklist = fetch_unfetchable_blocklist()
    known |= blocklist'''
assert rss_src.count(old_5b) == 1, f"edit 5b not found (count={rss_src.count(old_5b)})"
rss_src = rss_src.replace(old_5b, new_5b)

# --- Edit 5c: add pattern-based filter in candidate loop ---
old_5c = '''            for art in articles:
                url = art['url']
                if url in known:
                    continue
                # Only recent articles
                if art['pub_date'] and art['pub_date'] < cutoff:
                    continue'''
new_5c = '''            for art in articles:
                url = art['url']
                if url in known:
                    continue
                # Pattern-based unfetchable filter (Economist data pages, Bloomberg)
                if is_pattern_unfetchable(url, source):
                    continue
                # Only recent articles
                if art['pub_date'] and art['pub_date'] < cutoff:
                    continue'''
assert rss_src.count(old_5c) == 1, f"edit 5c not found (count={rss_src.count(old_5c)})"
rss_src = rss_src.replace(old_5c, new_5c)

# Syntax check
try:
    ast.parse(rss_src)
except SyntaxError as e:
    print(f"SYNTAX ERROR in patched rss_ai_pick.py: {e}")
    sys.exit(1)

RSS.write_text(rss_src)
print(f"rss_ai_pick.py: 3 edits applied, ast.parse OK, {len(rss_src)} chars")

# ─── 3: seed blocklist with existing 9 unfetchable URLs ─────────────────────
with sqlite3.connect(str(DB)) as cx:
    cx.execute("CREATE TABLE IF NOT EXISTS unfetchable_urls "
               "(url TEXT PRIMARY KEY, source TEXT, reason TEXT DEFAULT '', added_at INTEGER NOT NULL)")
    rows = cx.execute("SELECT url, source FROM articles WHERE status='unfetchable' AND url!=''").fetchall()
    import time
    ts = int(time.time() * 1000)
    seeded = 0
    for url, source in rows:
        cur = cx.execute(
            "INSERT OR IGNORE INTO unfetchable_urls (url, source, reason, added_at) VALUES (?,?,?,?)",
            (url, source or "", "seeded from existing unfetchable articles", ts)
        )
        if cur.rowcount > 0:
            seeded += 1
    # Also demote these from feed
    demoted = cx.execute("UPDATE articles SET auto_saved=0 WHERE status='unfetchable' AND auto_saved=1").rowcount
    cx.commit()
    total = cx.execute("SELECT COUNT(*) FROM unfetchable_urls").fetchone()[0]
print(f"blocklist: seeded {seeded} new URLs ({total} total), demoted {demoted} from feed")
print("ALL DONE")
