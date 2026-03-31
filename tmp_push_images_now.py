"""Push all 153 Mac images to VPS, including mac_id for correct dedup."""
import sqlite3, json, urllib.request, base64

MAC_DB = "/Users/alexdakers/meridian-server/meridian.db"
VPS    = "https://meridianreader.com/api/push-images"

conn = sqlite3.connect(MAC_DB)
rows = conn.execute(
    "SELECT id, article_id, caption, description, insight, image_data, width, height, captured_at "
    "FROM article_images "
    "WHERE insight != '' AND insight IS NOT NULL AND image_data IS NOT NULL"
).fetchall()
conn.close()
print(f"Mac total: {len(rows)} images")

images = [{
    "mac_id":      r[0],
    "article_id":  r[1],
    "caption":     r[2],
    "description": r[3],
    "insight":     r[4],
    "image_data":  base64.b64encode(r[5]).decode("ascii"),
    "width":       r[6],
    "height":      r[7],
    "captured_at": r[8],
} for r in rows]

total_upserted = 0
total_skipped  = 0
errors = 0
batch_size = 5
for i in range(0, len(images), batch_size):
    batch = images[i:i+batch_size]
    payload = json.dumps({"images": batch}).encode()
    req = urllib.request.Request(VPS, data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            u = result.get("upserted", 0)
            s = result.get("skipped", 0)
            total_upserted += u
            total_skipped  += s
            if u > 0:
                print(f"  Batch {i//batch_size+1}: +{u} new, {s} skipped")
    except Exception as e:
        errors += 1
        print(f"  Batch {i//batch_size+1} ERROR: {e}")

print(f"Done: {total_upserted} upserted, {total_skipped} skipped, {errors} errors")
