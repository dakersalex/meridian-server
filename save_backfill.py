import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

lines = content.split('\n')

# Find key line numbers
for i, line in enumerate(lines, 1):
    if 'FA_MOST_READ' in line or 'Filter to articles published' in line or 'Sort newest-first, then cap' in line or 'Per-source caps' in line:
        print(f"{i}: {line.rstrip()}")
