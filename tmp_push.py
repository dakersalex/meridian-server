import sqlite3, json, urllib.request, time

DB = "/Users/alexdakers/meridian-server/meridian.db"
VPS = "https://meridianreader.com/api/push-articles"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id,source,url,title,body,summary,topic,tags,saved_at,fetched_at,status,pub_date,auto_saved FROM articles WHERE status='full_text' ORDER BY saved_at DESC").fetchall()
conn.close()

arts = []
for r in rows:
    a = dict(r)
    try: a['tags'] = json.loads(a.get('tags') or '[]')
    except: a['tags'] = []
    arts.append(a)

print(f"Pushing {len(arts)} full_text articles...")
upserted = skipped = 0
for i in range(0, len(arts), 50):
    batch = arts[i:i+50]
    payload = json.dumps({'articles': batch}).encode()
    req = urllib.request.Request(VPS, data=payload, headers={'Content-Type':'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            r = json.loads(resp.read())
            upserted += r.get('upserted',0)
            skipped += r.get('skipped',0)
    except Exception as e:
        print(f"Batch {i//50+1} error: {e}")
    time.sleep(0.3)

print(f"Done: {upserted} upserted, {skipped} skipped of {len(arts)}")
