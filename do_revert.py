#!/usr/bin/env python3
"""
Revert server.py and meridian.html to pre-MCP commit 4f867800,
then re-apply only the two genuine fixes:
1. FT pub_date fallback to today
2. /api/articles/feed lean endpoint (single clean copy)
"""
import ast, subprocess, sys

# Step 1: Hard revert both files to pre-MCP state
print("Reverting to 4f867800...")
r = subprocess.run(
    ['git', 'checkout', '4f867800', '--', 'server.py', 'meridian.html'],
    cwd='/Users/alexdakers/meridian-server',
    capture_output=True, text=True
)
print(r.stdout or r.stderr or "reverted")

# Step 2: Verify syntax
with open('/Users/alexdakers/meridian-server/server.py') as f:
    content = f.read()
ast.parse(content)
print("server.py syntax OK")

# Step 3: Apply FT pub_date fix
old1 = "pub_date: a.publishedDate ? a.publishedDate.substring(0, 10) : '',"
new1 = "pub_date: a.publishedDate ? a.publishedDate.substring(0, 10) : new Date().toISOString().substring(0, 10),"
if old1 in content:
    content = content.replace(old1, new1, 1)
    print("FT feed pub_date fix applied")

old2 = "results.push({{title, url, source: 'Financial Times', pub_date: '', standfirst: '', is_opinion: false, is_podcast: false, already_saved: false}});"
new2 = "results.push({{title, url, source: 'Financial Times', pub_date: new Date().toISOString().substring(0, 10), standfirst: '', is_opinion: false, is_podcast: false, already_saved: false}});"
if old2 in content:
    content = content.replace(old2, new2, 1)
    print("FT DOM pub_date fix applied")

# Step 4: Add /api/articles/feed endpoint (single copy, before /api/health)
FEED_ENDPOINT = '''
@app.route("/api/articles/feed", methods=["GET"])
def get_articles_feed():
    """Lean feed — title/meta only, no body text. ~260KB vs ~3.6MB."""
    limit  = min(int(request.args.get("limit", 2000)), 5000)
    source = request.args.get("source", "")
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        q = ("SELECT id,source,url,title,topic,tags,status,pub_date,saved_at,auto_saved "
             "FROM articles {} "
             "ORDER BY COALESCE(NULLIF(pub_date,''),datetime(saved_at/1000,'unixepoch')) DESC LIMIT ?")
        if source:
            rows = cx.execute(q.format("WHERE source=?"), (source, limit)).fetchall()
        else:
            rows = cx.execute(q.format(""), (limit,)).fetchall()
    arts = []
    for r in rows:
        try: tags = json.loads(r["tags"] or "[]")
        except: tags = []
        arts.append({
            "id": r["id"], "source": r["source"], "url": r["url"],
            "title": r["title"], "topic": r["topic"] or "",
            "tags": tags, "status": r["status"],
            "pub_date": r["pub_date"] or "", "saved_at": r["saved_at"],
            "auto_saved": r["auto_saved"] or 0,
            "body": "", "summary": "",
        })
    return jsonify({"articles": arts, "total": len(arts)})

'''

ANCHOR = '@app.route("/api/health")'
assert content.count(FEED_ENDPOINT.strip()[:50]) == 0, "Feed endpoint already present"
assert ANCHOR in content
content = content.replace(ANCHOR, FEED_ENDPOINT + ANCHOR, 1)
print("Feed endpoint added (single copy)")

# Step 5: Final syntax check
ast.parse(content)
print("Final syntax OK")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)

# Step 6: Fix meridian.html to use /api/articles/feed
with open('/Users/alexdakers/meridian-server/meridian.html', 'r', encoding='utf-8') as f:
    html = f.read()

replacements = [
    ("fetch(SERVER+'/api/articles?limit=2000')", "fetch(SERVER+'/api/articles/feed?limit=2000')"),
    ("fetch(SERVER+'/api/articles?limit=500')", "fetch(SERVER+'/api/articles/feed?limit=500')"),
    ("fetch(SERVER + '/api/articles?limit=2000').then(r=>r.json()).then(d=>{ articles = d.articles || []; }).catch(()=>{})",
     "fetch(SERVER + '/api/articles/feed?limit=2000').then(r=>r.json()).then(d=>{ articles = d.articles || []; }).catch(()=>{})"),
    ("fetch(SERVER + '/api/articles?limit=2000'),",
     "fetch(SERVER + '/api/articles/feed?limit=2000'),"),
    ("const resp = await fetch(SERVER + '/api/articles?limit=2000');",
     "const resp = await fetch(SERVER + '/api/articles/feed?limit=2000');"),
]
for old, new in replacements:
    n = html.count(old)
    html = html.replace(old, new)
    if n: print(f"HTML: replaced {n}x {old[:50]}...")

with open('/Users/alexdakers/meridian-server/meridian.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("meridian.html updated")

# Step 7: Deploy
r = subprocess.run(
    ['./deploy.sh', 'Revert to pre-MCP state; FT pub_date fix; lean /api/articles/feed endpoint'],
    cwd='/Users/alexdakers/meridian-server',
    capture_output=True, text=True
)
print(r.stdout[-200:] if r.stdout else r.stderr[-200:])
print("DONE")
