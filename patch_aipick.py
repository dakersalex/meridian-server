import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

# Sort candidates newest-first before capping, so we always score the most recent articles
old = ('    # Cap candidates to avoid token limit and timeout issues\n'
       '    if len(candidates) > 50:\n'
       '        candidates = candidates[:50]\n'
       '        log.info(f"AI pick: capped candidates to 50")\n')
new = ('    # Sort newest-first, then cap at 50 to avoid token limit / timeout\n'
       '    candidates.sort(key=lambda a: a.get("pub_date",""), reverse=True)\n'
       '    if len(candidates) > 50:\n'
       '        candidates = candidates[:50]\n'
       '        log.info(f"AI pick: capped to 50 newest candidates")\n')
assert old in content, "cap pattern not found"
content = content.replace(old, new, 1)
print("Sort + cap applied")

ast.parse(content)
print("Syntax OK")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
