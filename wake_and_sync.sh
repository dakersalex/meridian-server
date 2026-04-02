#!/bin/bash
# Meridian wake-and-sync script
# Runs on Mac wake, triggers Playwright scrapers via the local Flask API
# Logs to ~/meridian-server/logs/wake_sync.log

LOG="$HOME/meridian-server/logs/wake_sync.log"
API="http://localhost:4242"

echo "$(date): Wake sync triggered" >> "$LOG"

# Wait for Flask to be ready (it should already be running via launchd)
for i in {1..12}; do
    if curl -s "$API/api/health" > /dev/null 2>&1; then
        break
    fi
    echo "$(date): Waiting for Flask... ($i)" >> "$LOG"
    sleep 5
done

# Trigger sync for all sources
echo "$(date): Triggering sync" >> "$LOG"
curl -s -X POST "$API/api/sync" \
  -H "Content-Type: application/json" \
  -d '{"sources":["ft","economist","fa"]}' >> "$LOG" 2>&1

echo "$(date): Sync triggered, waiting 90s for completion" >> "$LOG"
sleep 90

# Trigger enrichment of title-only articles
echo "$(date): Triggering enrichment" >> "$LOG"
curl -s -X POST "$API/api/enrich-title-only" >> "$LOG" 2>&1

# Push all full_text articles from Mac DB to VPS
# Pushes ALL full_text (no time window) so VPS stays in sync permanently.
# The VPS push-articles endpoint skips existing records with richer content, so this is safe to run every sync.
echo "$(date): Pushing articles to VPS" >> "$LOG"
python3 - << 'PYEOF' >> "$LOG" 2>&1
import sqlite3, json, urllib.request, time

DB = "/Users/alexdakers/meridian-server/meridian.db"
VPS = "https://meridianreader.com/api/push-articles"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = conn.execute("""
    SELECT id, source, url, title, body, summary, topic, tags,
           saved_at, fetched_at, status, pub_date, auto_saved
    FROM articles
    WHERE status = 'full_text'
    ORDER BY saved_at DESC
""").fetchall()
conn.close()

if not rows:
    print("push: no full_text articles to push")
else:
    arts = []
    for r in rows:
        a = dict(r)
        try: a['tags'] = json.loads(a.get('tags') or '[]')
        except: a['tags'] = []
        arts.append(a)

    total_upserted = 0
    total_skipped = 0
    batch_size = 50
    for i in range(0, len(arts), batch_size):
        batch = arts[i:i+batch_size]
        payload = json.dumps({'articles': batch}).encode()
        req = urllib.request.Request(VPS, data=payload,
            headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                total_upserted += result.get('upserted', 0)
                total_skipped += result.get('skipped', 0)
        except Exception as e:
            print(f"push batch error: {e}")
        time.sleep(0.3)

    print(f"push: {total_upserted} upserted, {total_skipped} skipped of {len(arts)} full_text articles")
PYEOF


# Push article_images (Economist charts) from Mac DB to VPS
echo "$(date): Pushing images to VPS" >> "$LOG"
python3 - << 'IMGEOF' >> "$LOG" 2>&1
import sqlite3, json, urllib.request, base64
DB = '/Users/alexdakers/meridian-server/meridian.db'
VPS = 'https://meridianreader.com/api/push-images'
conn = sqlite3.connect(DB)
q = 'SELECT id,article_id,caption,description,insight,image_data,width,height,captured_at FROM article_images WHERE insight != "" AND insight IS NOT NULL AND image_data IS NOT NULL'
rows = conn.execute(q).fetchall()
conn.close()
if not rows:
    print('push-images: no images to push')
else:
    images = [{'mac_id':r[0],'article_id':r[1],'caption':r[2],'description':r[3],'insight':r[4],'image_data':base64.b64encode(r[5]).decode('ascii'),'width':r[6],'height':r[7],'captured_at':r[8]} for r in rows]
    total_upserted = 0
    for i in range(0, len(images), 20):
        batch = images[i:i+20]
        payload = json.dumps({'images': batch}).encode()
        req = urllib.request.Request(VPS, data=payload, headers={'Content-Type':'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
                total_upserted += result.get('upserted', 0)
        except Exception as e:
            print(f'push-images batch error: {e}')
            break
    print(f'push-images: {total_upserted} upserted of {len(images)} total')
IMGEOF

echo "$(date): Wake sync complete" >> "$LOG"
