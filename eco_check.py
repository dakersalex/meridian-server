import ast
from datetime import datetime

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

# Fix 1: feed scrape — use today as fallback when publishedDate absent
old1 = "pub_date: a.publishedDate ? a.publishedDate.substring(0, 10) : '',"
new1 = "pub_date: a.publishedDate ? a.publishedDate.substring(0, 10) : new Date().toISOString().substring(0, 10),"
assert old1 in content, "Fix 1 not found"
content = content.replace(old1, new1, 1)
print("Fix 1: feed pub_date fallback to today")

# Fix 2: DOM fallback scrape — use today as fallback
old2 = "results.push({{title, url, source: 'Financial Times', pub_date: '', standfirst: '', is_opinion: false, is_podcast: false, already_saved: false}});"
new2 = "results.push({{title, url, source: 'Financial Times', pub_date: new Date().toISOString().substring(0, 10), standfirst: '', is_opinion: false, is_podcast: false, already_saved: false}});"
assert old2 in content, "Fix 2 not found"
content = content.replace(old2, new2, 1)
print("Fix 2: DOM fallback pub_date to today")

ast.parse(content)
print("Syntax OK")
with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
