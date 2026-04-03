
path = '/Users/alexdakers/meridian-server/server.py'
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

new_route = '''
@app.route("/api/push-newsletters", methods=["POST"])
def push_newsletters():
    """Receive newsletters from Mac and upsert into VPS DB."""
    data = request.json or {}
    newsletters = data.get("newsletters", [])
    if not newsletters:
        return jsonify({"ok": True, "upserted": 0, "skipped": 0})
    upserted = 0; skipped = 0
    with sqlite3.connect(DB_PATH) as cx:
        for n in newsletters:
            existing = cx.execute(
                "SELECT id FROM newsletters WHERE gmail_id=?", (n.get("gmail_id",""),)
            ).fetchone()
            if existing:
                skipped += 1
                continue
            cx.execute("""
                INSERT INTO newsletters (gmail_id, source, subject, body_html, body_text, received_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (n.get("gmail_id",""), n.get("source",""), n.get("subject",""),
                  n.get("body_html",""), n.get("body_text",""), n.get("received_at","")))
            upserted += 1
    log.info(f"push-newsletters: {upserted} upserted, {skipped} skipped of {len(newsletters)}")
    return jsonify({"ok": True, "upserted": upserted, "skipped": skipped})

@app.route("/api/push-interviews", methods=["POST"])
def push_interviews():
    """Receive interviews from Mac and upsert into VPS DB."""
    data = request.json or {}
    interviews = data.get("interviews", [])
    if not interviews:
        return jsonify({"ok": True, "upserted": 0, "skipped": 0})
    # Get interviews table schema
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        cols = [r["name"] for r in cx.execute("PRAGMA table_info(interviews)").fetchall()]
    upserted = 0; skipped = 0
    with sqlite3.connect(DB_PATH) as cx:
        for iv in interviews:
            existing = cx.execute(
                "SELECT id FROM interviews WHERE id=?", (iv.get("id"),)
            ).fetchone()
            if existing:
                skipped += 1
                continue
            fields = {k: v for k, v in iv.items() if k in cols}
            placeholders = ",".join(["?" for _ in fields])
            col_names = ",".join(fields.keys())
            cx.execute(f"INSERT INTO interviews ({col_names}) VALUES ({placeholders})",
                       list(fields.values()))
            upserted += 1
    log.info(f"push-interviews: {upserted} upserted, {skipped} skipped")
    return jsonify({"ok": True, "upserted": upserted, "skipped": skipped})

'''

# Insert before /api/push-articles
anchor = '@app.route("/api/push-articles"'
if anchor in src:
    src = src.replace(anchor, new_route + anchor)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(src)
    print('PATCHED OK')
else:
    print('NOT FOUND')
