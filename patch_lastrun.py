with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    content = f.read()

# Fix 1: last-run fetch missing SERVER prefix
old1 = "const lr = await fetch('/api/sync/last-run').then(r=>r.json());"
new1 = "const lr = await fetch(SERVER+'/api/sync/last-run').then(r=>r.json());"

# Fix 2: health-check fetch missing SERVER prefix
old2 = "const resp = await fetch('/api/health-check', {"
new2 = "const resp = await fetch(SERVER+'/api/health-check', {"

assert old1 in content, "Pattern 1 not found"
assert old2 in content, "Pattern 2 not found"

content = content.replace(old1, new1, 1)
content = content.replace(old2, new2, 1)

with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(content)

print("Both fixes applied")
