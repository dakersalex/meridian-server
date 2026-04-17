with open('/Users/alexdakers/meridian-server/vps_push.py', 'r') as f:
    content = f.read()

old = '''# ── Push suggested_articles to VPS ──────────────────────────────────────────
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
            VPS_BASE + '/api/push-suggested','''

new = '''# ── Push suggested_articles to VPS ──────────────────────────────────────────
# Push suggested articles added in last 48h (same window as articles)
try:
    with sqlite3.connect(DB) as cx:
        sug_rows = cx.execute("""
            SELECT title, url, source, snapshot_date, score, reason, added_at, status, pub_date
            FROM suggested_articles
            WHERE added_at >= ?
            AND url NOT LIKE '%ft.comhttps://%'
            AND url NOT LIKE '%#myft%'
        """, (cutoff_48h,)).fetchall()

    if sug_rows:
        cleaned = [[x if x is not None else '' for x in r] for r in sug_rows]
        sug_payload = json.dumps({'articles': cleaned}).encode()
        sug_req = urllib.request.Request(
            'https://meridianreader.com/api/push-suggested','''

assert old in content, f"Pattern not found"
content = content.replace(old, new, 1)
with open('/Users/alexdakers/meridian-server/vps_push.py', 'w') as f:
    f.write(content)
print("Fixed")
