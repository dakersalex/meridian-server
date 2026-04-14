with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    lines = f.readlines()

results = []
for i, line in enumerate(lines, 1):
    if 'push' in line.lower() and ('def ' in line or 'route' in line or 'upsert' in line or 'batch' in line):
        results.append(f"{i}: {line.rstrip()}")

with open('/Users/alexdakers/meridian-server/logs/push_grep.txt', 'w') as f:
    f.write('\n'.join(results))
print(f"Found {len(results)} lines")
