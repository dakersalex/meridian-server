import sqlite3, json, urllib.request, time

DB = "/Users/alexdakers/meridian-server/meridian.db"
VPS = "https://meridianreader.com/api/push-articles"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Push ALL full_text articles regardless of age — full backfill
rows = conn.execute("""
    SELECT id, source, url, title, body, summary, topic, tags,
           saved_at, fetched_at, status, pub_date, auto_saved
    FROM articles
    WHERE status = 'full_text'
    ORDER BY saved_at DESC
""").fetchall()
conn.close()

print(f"Total full_text articles to push: {len(rows)}")

arts = []
for r in rows:
    a = dict(r)
    try: a['tags'] = json.loads(a.get('tags') or '[]')
    except: a['tags'] = []
    arts.append(a)

# Push in batches of 50
batch_size = 50
total_upserted = 0
total_skipped = 0

for i in range(0, len(arts), batch_size):
    batch = arts[i:i+batch_size]
    payload = json.dumps({'articles': batch}).encode()
    req = urllib.request.Request(VPS, data=payload,
        headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            u = result.get('upserted', 0)
            s = result.get('skipped', 0)
            total_upserted += u
            total_skipped += s
            print(f"Batch {i//batch_size+1}: {u} upserted, {s} skipped")
    except Exception as e:
        print(f"Batch {i//batch_size+1} ERROR: {e}")
    time.sleep(0.5)  # gentle rate limiting

print(f"\nDone: {total_upserted} upserted, {total_skipped} skipped of {len(arts)} total")
