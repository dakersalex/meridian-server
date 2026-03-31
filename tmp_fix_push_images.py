"""
Fix push-images route: dedup on mac_id (the Mac autoincrement PK)
instead of (article_id, caption) which collides for multi-chart articles.
"""
import subprocess

path = "/Users/alexdakers/meridian-server/server.py"
with open(path, "r") as f:
    src = f.read()

OLD = '''@app.route("/api/push-images", methods=["POST"])
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
    return jsonify({"ok": True, "upserted": upserted, "skipped": skipped})'''

NEW = '''@app.route("/api/push-images", methods=["POST"])
def push_images():
    """Receive article_images rows from Mac and upsert into VPS DB.
    Deduplicates on mac_id (the Mac autoincrement PK) to correctly
    handle articles with multiple charts (all share the same caption).
    Called by wake_and_sync.sh after article push."""
    import base64 as _b64
    data = request.json or {}
    images = data.get("images", [])
    if not images:
        return jsonify({"ok": True, "upserted": 0})
    upserted = 0
    skipped = 0
    with sqlite3.connect(DB_PATH) as cx:
        # Ensure mac_id column exists (migration)
        cols = [r[1] for r in cx.execute("PRAGMA table_info(article_images)").fetchall()]
        if "mac_id" not in cols:
            cx.execute("ALTER TABLE article_images ADD COLUMN mac_id INTEGER DEFAULT NULL")
        for img in images:
            aid = img.get("article_id")
            if not aid:
                continue
            mac_id = img.get("mac_id")
            # Dedup by mac_id if provided, else fall back to article_id+description
            if mac_id is not None:
                existing = cx.execute(
                    "SELECT id FROM article_images WHERE mac_id=?", (mac_id,)).fetchone()
            else:
                existing = cx.execute(
                    "SELECT id FROM article_images WHERE article_id=? AND description=?",
                    (aid, img.get("description", ""))).fetchone()
            if existing:
                skipped += 1
                continue
            raw = img.get("image_data", "")
            blob = _b64.b64decode(raw) if isinstance(raw, str) else raw
            cx.execute(
                """INSERT INTO article_images
                   (article_id, caption, description, insight, image_data, width, height, captured_at, mac_id)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (aid,
                 img.get("caption", ""),
                 img.get("description", ""),
                 img.get("insight", ""),
                 blob,
                 img.get("width", 0),
                 img.get("height", 0),
                 img.get("captured_at", now_ts()),
                 mac_id))
            upserted += 1
    log.info(f"push-images: upserted {upserted}, skipped {skipped} of {len(images)}")
    return jsonify({"ok": True, "upserted": upserted, "skipped": skipped})'''

assert OLD in src, "OLD route not found in server.py"
src = src.replace(OLD, NEW, 1)
with open(path, "w") as f:
    f.write(src)

result = subprocess.run(["python3", "-m", "py_compile", path], capture_output=True, text=True)
if result.returncode == 0:
    print("server.py COMPILE_OK")
else:
    print("COMPILE_FAIL:", result.stderr)
