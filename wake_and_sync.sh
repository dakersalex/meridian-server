#!/bin/bash
# Meridian wake-and-sync script
# Runs on schedule via launchd (05:40 and 11:40 Geneva time)
# Article discovery: RSS picks (automated) + Chrome extension auto-sync (every 2h)
# Body fetching: Chrome extension background fetcher (every 15min)
# This script handles: RSS picks, newsletter sync, VPS push, health check

LOG="$HOME/meridian-server/logs/wake_sync.log"
API="http://localhost:4242"

echo "$(date): Wake sync triggered" >> "$LOG"

# Wait for Flask to be ready
for i in {1..12}; do
    if curl -s "$API/api/health" > /dev/null 2>&1; then
        break
    fi
    echo "$(date): Waiting for Flask... ($i)" >> "$LOG"
    sleep 5
done

# RSS-based AI pick — discovers new articles from FT/Economist/FA RSS feeds
echo "$(date): Running RSS-based AI pick" >> "$LOG"
curl -s -X POST "$API/api/rss-pick" >> "$LOG" 2>&1
sleep 15

# Trigger newsletter sync from iCloud IMAP
echo "$(date): Syncing newsletters from iCloud" >> "$LOG"
curl -s -X POST "$API/api/newsletters/sync" >> "$LOG" 2>&1
sleep 15

# Push new/updated articles to VPS
echo "$(date): Pushing articles to VPS" >> "$LOG"
python3 /Users/alexdakers/meridian-server/vps_push.py >> "$LOG" 2>&1

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

# Push newsletters from Mac DB to VPS
echo "$(date): Pushing newsletters to VPS" >> "$LOG"
python3 - << 'NLEOF' >> "$LOG" 2>&1
import sqlite3, json, urllib.request, time
DB = '/Users/alexdakers/meridian-server/meridian.db'
VPS = 'https://meridianreader.com/api/push-newsletters'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = conn.execute(
    'SELECT gmail_id, source, subject, body_html, body_text, received_at FROM newsletters ORDER BY received_at DESC'
).fetchall()
conn.close()
if not rows:
    print('push-newsletters: no newsletters to push')
else:
    newsletters = [dict(r) for r in rows]
    total_upserted = 0; total_skipped = 0
    batch_size = 20
    for i in range(0, len(newsletters), batch_size):
        batch = newsletters[i:i+batch_size]
        payload = json.dumps({'newsletters': batch}).encode()
        req = urllib.request.Request(VPS, data=payload, headers={'Content-Type':'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                total_upserted += result.get('upserted', 0)
                total_skipped += result.get('skipped', 0)
        except Exception as e:
            print(f'push-newsletters batch error: {e}')
        time.sleep(0.2)
    print(f'push-newsletters: {total_upserted} upserted, {total_skipped} skipped of {len(newsletters)} total')
NLEOF

# Push interviews from Mac DB to VPS
echo "$(date): Pushing interviews to VPS" >> "$LOG"
python3 - << 'IVEOF' >> "$LOG" 2>&1
import sqlite3, json, urllib.request
DB = '/Users/alexdakers/meridian-server/meridian.db'
VPS = 'https://meridianreader.com/api/push-interviews'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = conn.execute(
    'SELECT id, title, url, source, published_date, added_date, duration_seconds, transcript, summary, status, thumbnail_url, speaker_bio FROM interviews'
).fetchall()
conn.close()
if not rows:
    print('push-interviews: no interviews to push')
else:
    interviews = [dict(r) for r in rows]
    payload = json.dumps({'interviews': interviews}).encode()
    req = urllib.request.Request(VPS, data=payload, headers={'Content-Type':'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            print(f'push-interviews: {result.get("upserted",0)} upserted, {result.get("skipped",0)} skipped of {len(interviews)} total')
    except Exception as e:
        print(f'push-interviews error: {e}')
IVEOF

# Log enrichment health check
echo "$(date): Enrichment health check:" >> "$LOG"
curl -s "$API/api/health/enrichment" >> "$LOG" 2>&1
echo "" >> "$LOG"

echo "$(date): Wake sync complete" >> "$LOG"
