with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    lines = f.readlines()

# Find API_BASE or port 4242 references near the stats block
results = []
for i, line in enumerate(lines, 1):
    if 'API_BASE' in line or '4242' in line or "'/api/" in line or '"/api/' in line:
        results.append(f"{i}: {line.rstrip()}")

with open('/Users/alexdakers/meridian-server/logs/apibase_result.txt', 'w') as f:
    f.write('\n'.join(results[:60]))
print(f"Found {len(results)} lines")
