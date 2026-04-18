with open('/Users/alexdakers/meridian-server/meridian.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Switch main load calls from /api/articles to /api/articles/feed
# The full /api/articles is still needed for article detail view (body/summary)
replacements = [
    # Main loadFromServer call
    ("fetch(SERVER+'/api/articles?limit=2000')", "fetch(SERVER+'/api/articles/feed?limit=2000')"),
    # Briefing generator fetch
    ("fetch(SERVER+'/api/articles?limit=500')", "fetch(SERVER+'/api/articles/feed?limit=500')"),
    # Key themes fetch
    ("fetch(SERVER + '/api/articles?limit=2000').then(r=>r.json()).then(d=>{ articles = d.articles || []; }).catch(()=>{})", 
     "fetch(SERVER + '/api/articles/feed?limit=2000').then(r=>r.json()).then(d=>{ articles = d.articles || []; }).catch(()=>{})"),
]

count = 0
for old, new in replacements:
    n = content.count(old)
    content = content.replace(old, new)
    count += n
    print(f"Replaced {n}x: {old[:60]}...")

assert content.count('<html lang') == 1
with open('/Users/alexdakers/meridian-server/meridian.html', 'w', encoding='utf-8') as f:
    f.write(content)
print(f"Done — {count} replacements")
