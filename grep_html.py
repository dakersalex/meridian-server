import re

with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    lines = f.readlines()

patterns = ['last-run', 'daysAgo', 'timeAgo', 'LAST SCRAPED', 'lastScraped', 'sync/last', 'Last Scraped', 'scrape_label', 'relativeTime', 'relative_time']

results = []
for i, line in enumerate(lines, 1):
    for p in patterns:
        if p.lower() in line.lower():
            results.append(f"{i}: {line.rstrip()}")
            break

with open('/Users/alexdakers/meridian-server/logs/grep_result.txt', 'w') as f:
    f.write('\n'.join(results))

print(f"Found {len(results)} lines")
