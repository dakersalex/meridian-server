with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

# Find sync_status definition
lines = content.split('\n')
found = []
for i, line in enumerate(lines, 1):
    if 'sync_status' in line and '=' in line and 'def ' not in line and '.get' not in line and 'not sync_status' not in line:
        found.append(f"{i}: {line}")
    if line.startswith('SCRAPERS'):
        found.append(f"SCRAPERS at {i}: {line}")
    if 'def run_sync' in line:
        found.append(f"run_sync at {i}: {line}")

with open('/Users/alexdakers/meridian-server/logs/syncstatus.txt', 'w') as f:
    f.write('\n'.join(found))
print('\n'.join(found))
