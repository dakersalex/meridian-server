"""
Patch server.py: add POST /api/push-images route after push-articles.
Receives article_images rows from Mac and upserts them into VPS DB.
"""
path = "/Users/alexdakers/meridian-server/server.py"
with open(path, "r") as f:
    src = f.read()

NEW_ROUTE = '''
@app.route("/api/push-images", methods=["POST"])
def push_images():
    """Receive article_images rows from Mac and upsert into VPS DB.
    Called by wake_and_sync.sh after article push."""
    data = request.json or {}
    images = data.get("images", [])
    if not images:
        return jsonify({"ok": True, "upserted": 0})
    upserted = 0
    skipped = 0
    with sqlite3.connect(DB_PATH) as cx:
        for img in images:
            aid = img.get("article_id")
            caption = img.get("caption", "")
            if not aid or not caption:
                continue
            existing = cx.execute(
                "SELECT id FROM article_images WHERE article_id=? AND caption=?",
                (aid, caption)).fetchone()
            if existing:
                skipped += 1
                continue
            import base64
            raw = img.get("image_data", "")
            blob = base64.b64decode(raw) if isinstance(raw, str) else raw
            cx.execute(
                """INSERT INTO article_images
                   (article_id, caption, description, insight, image_data, width, height, captured_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (aid, caption,
                 img.get("description", ""),
                 img.get("insight", ""),
                 blob,
                 img.get("width", 0),
                 img.get("height", 0),
                 img.get("captured_at", now_ts())))
            upserted += 1
    log.info(f"push-images: upserted {upserted}, skipped {skipped} of {len(images)}")
    return jsonify({"ok": True, "upserted": upserted, "skipped": skipped})

'''

# Insert after the push_articles function (before the dev/shell route)
marker = '@app.route("/api/dev/shell", methods=["POST"])'
assert marker in src, "Marker not found"
src = src.replace(marker, NEW_ROUTE + marker, 1)

with open(path, "w") as f:
    f.write(src)

import subprocess
result = subprocess.run(["python3", "-m", "py_compile", path], capture_output=True, text=True)
if result.returncode == 0:
    print("server.py COMPILE_OK")
else:
    print("COMPILE_FAIL:", result.stderr)
