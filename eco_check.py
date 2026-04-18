import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

# The duplicate block — first occurrence was inserted before /api/health
# Second occurrence was inserted again in the same place on a subsequent patch
# Strategy: find the FIRST complete enrich-via-browser block and remove it,
# keeping only the second (more complete) one

MARKER_START = '\n@app.route("/api/enrich-via-browser", methods=["GET"])\ndef enrich_via_browser_list():'
MARKER_END = '\n@app.route("/api/health")'

first = content.find(MARKER_START)
second = content.find(MARKER_START, first + 1)

print(f"First occurrence at char: {first}")
print(f"Second occurrence at char: {second}")

if second > 0:
    # Remove the first block (from first to just before second)
    content = content[:first] + content[second:]
    print("Removed first duplicate block")
else:
    print("No duplicate found — nothing to remove")

# Verify
remaining = content.count(MARKER_START)
print(f"Remaining enrich_via_browser_list routes: {remaining}")

ast.parse(content)
print("Syntax OK")
with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Saved")
