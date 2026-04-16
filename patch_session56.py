import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

old = '"/gift", "/audio", "/video", "/events", "/browse/",\n        "/authors/", "/staff", "/collections/", "/book-reviews/",'
new = '"/gift", "/audio", "/video", "/events", "/browse/",\n        "/authors/", "/staff", "/collections/", "/book-reviews/", "/podcasts/",'

assert old in content, "SKIP_PREFIXES pattern not found"
content = content.replace(old, new, 1)

ast.parse(content)
print("Syntax OK")
with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
