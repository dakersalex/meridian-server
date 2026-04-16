with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    lines = f.readlines()

chunk = lines[1924:1950]
with open('/Users/alexdakers/meridian-server/logs/cap_block.txt', 'w') as f:
    for i, line in enumerate(chunk, 1925):
        f.write(f"{i}: {line}")
print("done")
