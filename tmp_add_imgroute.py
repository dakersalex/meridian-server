
path = '/Users/alexdakers/meridian-server/server.py'
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

# Insert new route just before the backfill route
new_route = '''
@app.route("/api/images/recent", methods=["GET"])
def images_recent():
    """Return the most recent N images as base64 for progress monitoring.
    Query params: limit (default 20), every_nth (default 5, returns every nth image by id)"""
    import base64
    limit = int(request.args.get("limit", 20))
    every_nth = int(request.args.get("every_nth", 5))
    with get_db() as db:
        rows = db.execute(
            "SELECT id, article_id, caption, description, image_data, captured_at FROM article_images ORDER BY id DESC LIMIT ?",
            (limit * every_nth,)
        ).fetchall()
    # Take every nth row so we show a sample
    sampled = rows[::every_nth][:limit]
    result = []
    for row in sampled:
        img_b64 = base64.b64encode(row["image_data"]).decode("utf-8") if row["image_data"] else None
        result.append({
            "id": row["id"],
            "article_id": row["article_id"],
            "caption": row["caption"],
            "description": row["description"],
            "image_b64": img_b64,
            "captured_at": row["captured_at"],
        })
    total = db_query_one("SELECT COUNT(*) as n FROM article_images")["n"]
    return jsonify({"images": result, "total": total})

'''

old = '@app.route("/api/images/backfill", methods=["POST"])'
if old in src:
    src = src.replace(old, new_route + old)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(src)
    print('PATCHED OK')
else:
    print('NOT FOUND')
