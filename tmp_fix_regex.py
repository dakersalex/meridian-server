"""Fix literal newlines inside JS regex literals in meridian.html introduced by patch script."""
path = "/Users/alexdakers/meridian-server/meridian.html"
with open(path, "rb") as f:
    raw = f.read()

# Fix 1: (<li>.*<\/li>\n?)+  — \n became real newline
raw = raw.replace(
    b'(<li>.*<\\/li>\n?)',
    b'(<li>.*<\\/li>\\n?)'
)

# Fix 2: /\n\n/g — \n\n became two real newlines inside regex
raw = raw.replace(
    b'.replace(/\n\n/g',
    b'.replace(/\\n\\n/g'
)

with open(path, "wb") as f:
    f.write(raw)

print("Fixed OK")
