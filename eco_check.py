with open('/Users/alexdakers/meridian-server/meridian.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix remaining stale full-article calls
old = "fetch(SERVER + '/api/articles?limit=2000'),"
new = "fetch(SERVER + '/api/articles/feed?limit=2000'),"
n = content.count(old)
content = content.replace(old, new)
print(f"Fixed {n}x briefing generator call")

old2 = "const resp = await fetch(SERVER + '/api/articles?limit=2000');"
new2 = "const resp = await fetch(SERVER + '/api/articles/feed?limit=2000');"
n2 = content.count(old2)
content = content.replace(old2, new2)
print(f"Fixed {n2}x key themes call")

assert content.count('<html lang') == 1
with open('/Users/alexdakers/meridian-server/meridian.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
