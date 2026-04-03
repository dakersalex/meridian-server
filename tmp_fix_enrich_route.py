
path = '/Users/alexdakers/meridian-server/server.py'
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

old = '''@app.route("/api/enrich/<aid>", methods=["POST"])
def enrich_article(aid):
    with sqlite3.connect(DB_PATH) as cx:
        row = cx.execute("SELECT * FROM articles WHERE id=?", (aid,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Not found"}), 404
    art = dict(zip([d[0] for d in cx.description], row))
    enrich_article_with_ai(art)
    return jsonify({"ok": True})'''

new = '''@app.route("/api/enrich/<aid>", methods=["POST"])
def enrich_article(aid):
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        row = cx.execute("SELECT * FROM articles WHERE id=?", (aid,)).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Not found"}), 404
        art = dict(row)
    enriched = enrich_article_with_ai(art)
    summary = enriched.get("summary", "")
    if summary:
        with sqlite3.connect(DB_PATH) as cx2:
            cx2.execute(
                "UPDATE articles SET summary=?, tags=?, topic=?, pub_date=? WHERE id=?",
                (summary, enriched.get("tags","[]"), enriched.get("topic",""),
                 enriched.get("pub_date", art.get("pub_date","")), aid)
            )
    return jsonify({"ok": True, "summary_len": len(summary)})'''

if old in src:
    src = src.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(src)
    print('PATCHED OK')
else:
    print('NOT FOUND')
