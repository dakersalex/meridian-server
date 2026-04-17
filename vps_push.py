import sqlite3, json, urllib.request, time

DB = "/Users/alexdakers/meridian-server/meridian.db"
VPS_ARTICLES = "https://meridianreader.com/api/push-articles"
VPS_META = "https://meridianreader.com/api/push-meta"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

now_ms = int(time.time() * 1000)
cutoff_48h = now_ms - (48 * 3600 * 1000)

wm_row = conn.execute("SELECT value FROM kt_meta WHERE key='last_push_ts'").fetchone()
if wm_row:
    last_push_ms = int(wm_row[0])
    cutoff = min(last_push_ms, cutoff_48h)
else:
    cutoff = now_ms - (7 * 24 * 3600 * 1000)

rows = conn.execute(
    "SELECT id, source, url, title, body, summary, topic, tags, saved_at, fetched_at, status, pub_date, auto_saved "
    "FROM articles WHERE saved_at >= ? AND status IN ('full_text','fetched','title_only','agent') ORDER BY saved_at ASC",
    (cutoff,)
).fetchall()

meta_rows = conn.execute(
    "SELECT key, value FROM kt_meta WHERE key LIKE 'last_sync_%'"
).fetchall()
conn.close()

total_upserted = 0
total_skipped = 0

if not rows:
    print("push: 0 new articles since watermark")
else:
    arts = []
    for r in rows:
        a = dict(r)
        try:
            a['tags'] = json.loads(a.get('tags') or '[]')
        except Exception:
            a['tags'] = []
        arts.append(a)

    batch_size = 50
    for i in range(0, len(arts), batch_size):
        batch = arts[i:i + batch_size]
        payload = json.dumps({'articles': batch}).encode()
        req = urllib.request.Request(VPS_ARTICLES, data=payload,
            headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                total_upserted += result.get('upserted', 0)
                total_skipped += result.get('skipped', 0)
        except Exception as e:
            print("push batch error: " + str(e))
        time.sleep(0.3)

    print("push: " + str(total_upserted) + " upserted, " + str(total_skipped) + " skipped of " + str(len(arts)) + " articles")

# Update watermark
conn2 = sqlite3.connect(DB)
conn2.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES ('last_push_ts', ?)", (str(now_ms),))
conn2.commit()
conn2.close()

# Always push kt_meta last_sync timestamps to VPS
if meta_rows:
    pairs = {k: v for k, v in meta_rows}
    payload = json.dumps({'pairs': pairs}).encode()
    req = urllib.request.Request(VPS_META, data=payload,
        headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            print("push-meta: " + str(result.get('upserted', 0)) + " keys synced to VPS")
    except Exception as e:
        print("push-meta error: " + str(e))

# ── Push suggested_articles to VPS ──────────────────────────────────────────
# Push suggested articles added in last 48h (same window as articles)
try:
    with sqlite3.connect(DB_PATH) as cx:
        sug_rows = cx.execute("""
            SELECT title, url, source, snapshot_date, score, reason, added_at, status, pub_date
            FROM suggested_articles
            WHERE added_at >= ?
            AND url NOT LIKE '%ft.comhttps://%'
            AND url NOT LIKE '%#myft%'
        """, (int((now - 172800) * 1000),)).fetchall()

    if sug_rows:
        cleaned = [[x if x is not None else '' for x in r] for r in sug_rows]
        sug_payload = json.dumps({'articles': cleaned}).encode()
        sug_req = urllib.request.Request(
            VPS_BASE + '/api/push-suggested',
            data=sug_payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            with urllib.request.urlopen(sug_req, timeout=30) as resp:
                result = json.loads(resp.read())
                print("push-suggested: " + str(result.get('added', 0)) + " new suggested articles synced to VPS")
        except Exception as e:
            print("push-suggested error: " + str(e))
except Exception as e:
    print("push-suggested local error: " + str(e))
