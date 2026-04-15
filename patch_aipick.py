import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

# Fix the filter to pass through blank pub_dates (FA articles)
old = '    candidates = [a for a in candidates if a.get("pub_date","") >= _cutoff]\n'
new = '    candidates = [a for a in candidates if not a.get("pub_date") or a.get("pub_date","") >= _cutoff]\n'

assert old in content, "Pattern not found"
content = content.replace(old, new, 1)

ast.parse(content)
print("Syntax OK")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
