with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    lines = f.readlines()

# Show lines 1795-1830 to see how candidates are ordered before scoring
for i, line in enumerate(lines[1794:1832], 1795):
    print(f"{i}: {line.rstrip()}")
