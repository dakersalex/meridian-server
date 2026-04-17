import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

# Add after /api/push-meta endpoint
old_anchor = '@app.route("/api/push-meta", methods=["POST"])'
assert old_anchor in content, "anchor not found"

new_endpoint = '''@app.route("/api/push-suggested", methods=["POST"])
def push_suggested():
    """Receive suggested articles from Mac and upsert to VPS DB."""
    data = request.json or {}
    articles = data.get("articles", [])
    with sqlite3.connect(DB_PATH) as cx:
        existing = set(r[0] for r in cx.execute("SELECT url FROM suggested_articles").fetchall())
        added = 0
        for a in articles:
            if len(a) < 9: continue
            title, url, source, snapshot_date, score, reason, added_at, status, pub_date = a[:9]
            if not url or url in existing: continue
            cx.execute(
                "INSERT INTO suggested_articles (title,url,source,snapshot_date,score,reason,added_at,status,pub_date) VALUES (?,?,?,?,?,?,?,?,?)",
                (title, url, source, snapshot_date, score, reason, added_at, status, pub_date)
            )
            existing.add(url)
            added += 1
    return jsonify({"ok": True, "added": added})


'''

content = content.replace(old_anchor, new_endpoint + old_anchor, 1)

ast.parse(content)
print("Syntax OK")
with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
