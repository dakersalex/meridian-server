with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    lines = f.readlines()

# Show lines around _known definition at line 1647
for i, line in enumerate(lines[1635:1655], 1636):
    print(f"{i}: {line.rstrip()}")
