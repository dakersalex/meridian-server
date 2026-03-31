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

# Push recently-synced articles from Mac DB to VPS
echo "$(date): Pushing new articles to VPS" >> "$LOG"
python3 - << 'PYEOF' >> "$LOG" 2>&1
import sqlite3, json, urllib.request, time

DB = "/Users/alexdakers/meridian-server/meridian.db"
VPS = "https://meridianreader.com/api/push-articles"

# Push recently-synced/enriched articles from Mac to VPS:
# - Foreign Affairs: all
# - FT/Economist auto_saved=1: agent picks
# - FT/Economist auto_saved=0 full_text: your bookmarks that have been enriched
cutoff = int((time.time() - 3*60*60) * 1000)
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = conn.execute("""
    SELECT id, source, url, title, body, summary, topic, tags,
           saved_at, fetched_at, status, pub_date, auto_saved
    FROM articles
    WHERE (
        (saved_at >= ? AND source = 'Foreign Affairs')
        OR (saved_at >= ? AND source IN ('Financial Times','The Economist') AND auto_saved = 1)
        OR (source IN ('Financial Times','The Economist') AND auto_saved = 0 AND status = 'full_text'
            AND fetched_at >= ?)
    )
    ORDER BY saved_at DESC
""", (cutoff, cutoff, cutoff)).fetchall()
conn.close()

if not rows:
    print(f"push: no recent articles to push")
else:
    arts = []
    for r in rows:
        a = dict(r)
        try: a['tags'] = json.loads(a.get('tags') or '[]')
        except: a['tags'] = []
        arts.append(a)
    payload = json.dumps({'articles': arts}).encode()
    req = urllib.request.Request(VPS, data=payload,
        headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            print(f"push: {result.get('upserted',0)} upserted, {result.get('skipped',0)} skipped of {len(arts)}")
    except Exception as e:
        print(f"push error: {e}")
PYEOF


# Push article_images (Economist charts) from Mac DB to VPS
echo "$(date): Pushing images to VPS" >> "$LOG"
python3 - << 'IMGEOF' >> "$LOG" 2>&1
import sqlite3, json, urllib.request, base64
DB = '/Users/alexdakers/meridian-server/meridian.db'
VPS = 'https://meridianreader.com/api/push-images'
conn = sqlite3.connect(DB)
q = 'SELECT article_id,caption,description,insight,image_data,width,height,captured_at FROM article_images WHERE insight != "" AND insight IS NOT NULL AND image_data IS NOT NULL'
rows = conn.execute(q).fetchall()
conn.close()
if not rows:
    print('push-images: no images to push')
else:
    images = [{'article_id':r[0],'caption':r[1],'description':r[2],'insight':r[3],'image_data':base64.b64encode(r[4]).decode('ascii'),'width':r[5],'height':r[6],'captured_at':r[7]} for r in rows]
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
