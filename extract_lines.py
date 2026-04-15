with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    lines = f.readlines()

# Find _now_h definition and score threshold
for i, line in enumerate(lines, 1):
    if '_now_h' in line or 'score' in line.lower() and '>=' in line and ('8' in line or '9' in line or '7' in line):
        print(f"{i}: {line.rstrip()}")
