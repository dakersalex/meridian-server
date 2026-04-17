import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

# Add relay endpoint — uses a simple in-memory queue that Claude MCP polls
NEW_ENDPOINTS = '''
@app.route("/api/enrich-via-browser", methods=["GET"])
def enrich_via_browser_list():
    """Return title_only articles grouped by source for Claude Chrome MCP enrichment."""
    with sqlite3.connect(DB_PATH) as cx:
        rows = cx.execute("""
            SELECT id, source, url, title
            FROM articles
            WHERE status='title_only' AND url != ''
            ORDER BY source, saved_at DESC
        """).fetchall()
    by_source = {}
    for row in rows:
        src = row[1]
        if src not in by_source:
            by_source[src] = []
        by_source[src].append({"id": row[0], "source": src, "url": row[2], "title": row[3]})
    total = sum(len(v) for v in by_source.values())
    return jsonify({"by_source": by_source, "total": total})


@app.route("/api/enrich-via-browser/relay", methods=["POST"])
def enrich_via_browser_relay():
    """Relay endpoint: browser posts article to enrich, Claude MCP navigates and returns body."""
    data = request.json or {}
    art_id = data.get("id", "")
    url = data.get("url", "")
    if not art_id or not url:
        return jsonify({"ok": False, "error": "Missing id or url"})
    # Return the article details — Claude MCP will navigate, get text, POST back to /api/enrich-via-browser/{id}
    return jsonify({"ok": True, "id": art_id, "url": url, "action": "navigate_and_extract"})


@app.route("/api/enrich-via-browser/<aid>", methods=["POST"])
def enrich_via_browser_save(aid):
    """Receive full article text from Chrome MCP and save to DB, then AI-enrich."""
    data = request.json or {}
    body = (data.get("body") or "").strip()
    if not body or len(body) < 100:
        return jsonify({"ok": False, "error": "Body too short or empty"})
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute(
            "UPDATE articles SET body=?, status='fetched', fetched_at=? WHERE id=? AND status='title_only'",
            (body, now_ts(), aid)
        )
        changed = cx.execute("SELECT changes()").fetchone()[0]
    if changed:
        with sqlite3.connect(DB_PATH) as cx:
            row = cx.execute("SELECT * FROM articles WHERE id=?", (aid,)).fetchone()
        if row:
            art = dict(row)
            try: art["tags"] = json.loads(art.get("tags") or "[]")
            except: art["tags"] = []
            import threading
            threading.Thread(target=enrich_article_with_ai, args=(art,), daemon=True).start()
        log.info(f"Enrich-via-browser: saved body for {aid} ({len(body)} chars)")
        return jsonify({"ok": True, "id": aid, "chars": len(body)})
    return jsonify({"ok": False, "error": "Article not found or already enriched"})

'''

ANCHOR = '@app.route("/api/health")'
assert ANCHOR in content, "anchor not found"
content = content.replace(ANCHOR, NEW_ENDPOINTS + ANCHOR, 1)

ast.parse(content)
print("Syntax OK")
with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
