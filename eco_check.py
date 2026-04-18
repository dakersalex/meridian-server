import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

NEW_ENDPOINT = '''
@app.route("/api/articles/feed", methods=["GET"])
def get_articles_feed():
    """Lean feed — title/meta only, no body text. 260KB vs 3.6MB for fast page loads."""
    limit  = min(int(request.args.get("limit", 2000)), 5000)
    source = request.args.get("source", "")
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        q = ("SELECT id,source,url,title,topic,tags,status,pub_date,saved_at,auto_saved "
             "FROM articles {} "
             "ORDER BY COALESCE(NULLIF(pub_date,''),datetime(saved_at/1000,'unixepoch')) DESC LIMIT ?")
        if source:
            rows = cx.execute(q.format("WHERE source=?"), (source, limit)).fetchall()
        else:
            rows = cx.execute(q.format(""), (limit,)).fetchall()
    arts = []
    for r in rows:
        try: tags = json.loads(r["tags"] or "[]")
        except: tags = []
        arts.append({
            "id": r["id"], "source": r["source"], "url": r["url"],
            "title": r["title"], "topic": r["topic"] or "",
            "tags": tags, "status": r["status"],
            "pub_date": r["pub_date"] or "", "saved_at": r["saved_at"],
            "auto_saved": r["auto_saved"] or 0,
            "body": "", "summary": "",
        })
    return jsonify({"articles": arts, "total": len(arts)})

'''

ANCHOR = '@app.route("/api/health")'
assert ANCHOR in content
content = content.replace(ANCHOR, NEW_ENDPOINT + ANCHOR, 1)
ast.parse(content)
print("Syntax OK")
with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
