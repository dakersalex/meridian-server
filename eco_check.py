import ast, re

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

MARKER = '@app.route("/api/articles/feed", methods=["GET"])\ndef get_articles_feed():'
count = content.count(MARKER)
print(f"get_articles_feed occurrences: {count}")

if count > 1:
    # Keep only the last occurrence, remove all earlier ones
    ANCHOR = '@app.route("/api/health")'
    idx_first = content.find(MARKER)
    idx_second = content.find(MARKER, idx_first + 1)
    idx_health = content.find('\n' + ANCHOR)
    # Remove everything from first occurrence up to (but not including) second
    content = content[:idx_first] + content[idx_second:]
    print(f"Removed first duplicate")

remaining = content.count(MARKER)
print(f"Remaining: {remaining}")

ast.parse(content)
print("Syntax OK")
with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
