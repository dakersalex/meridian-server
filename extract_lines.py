with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    lines = f.readlines()

results = []
for i, line in enumerate(lines, 1):
    if 'swim' in line.lower() or ('lane' in line.lower() and 'date' in line.lower()):
        results.append(f"{i}: {line.rstrip()}")
    if 'articleDate' in line or 'article_date' in line or ('pub_date' in line and 'saved_at' in line):
        results.append(f"{i}: {line.rstrip()}")

with open('/Users/alexdakers/meridian-server/logs/swimlane_logic.txt', 'w') as f:
    f.write('\n'.join(results[:40]))
print(f"Found {len(results)}")
