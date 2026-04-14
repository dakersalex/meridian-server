with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

new_endpoint = '''
@app.route("/api/push-meta", methods=["POST"])
def push_meta():
    """Receive kt_meta key-value pairs from Mac and upsert into VPS kt_meta.
    Used to sync last_sync_* timestamps and other operational flags."""
    data = request.json or {}
    pairs = data.get("pairs", {})
    if not pairs:
        return jsonify({"ok": True, "upserted": 0})
    upserted = 0
    with sqlite3.connect(DB_PATH) as cx:
        for key, value in pairs.items():
            cx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES (?, ?)", (key, str(value)))
            upserted += 1
    log.info(f"push-meta: {upserted} keys upserted")
    return jsonify({"ok": True, "upserted": upserted})

'''

old = '@app.route("/api/push-images", methods=["POST"])'
assert old in content, "Anchor not found"
content = content.replace(old, new_endpoint + old, 1)

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)

print("push-meta endpoint added")
