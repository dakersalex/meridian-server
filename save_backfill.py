import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

# Add title filter to _extract_articles in FA scraper
old = (
    '            # Skip nav-like titles\n'
    '            if title in ("Current Issue", "Browse by Section", "Most Recent",\n'
    '                         "Most Read", "All Regions", "Issue Archive",\n'
    '                         "Author Directory", "Book Reviews", "Audio Articles"):\n'
    '                continue'
)
new = (
    '            # Skip nav-like and non-article titles\n'
    '            if title in ("Current Issue", "Browse by Section", "Most Recent",\n'
    '                         "Most Read", "All Regions", "Issue Archive",\n'
    '                         "Author Directory", "Book Reviews", "Audio Articles",\n'
    '                         "Recent Books"):\n'
    '                continue\n'
    '            # Skip book review index pages\n'
    '            if "/book-reviews/" in href:\n'
    '                continue'
)

if old in content:
    content = content.replace(old, new, 1)
    print("Title filter updated")
else:
    # FA scraper was rebuilt — find the equivalent skip block
    old2 = (
        '            # Title must be meaningful\n'
        '            if not title or len(title) < 8:\n'
        '                continue'
    )
    new2 = (
        '            # Title must be meaningful\n'
        '            if not title or len(title) < 8:\n'
        '                continue\n'
        '            # Skip book review index pages and generic nav titles\n'
        '            if "/book-reviews/" in href:\n'
        '                continue\n'
        '            if title in ("Recent Books", "Book Reviews", "Current Issue",\n'
        '                         "Most Read", "Author Directory", "Audio Articles"):\n'
        '                continue'
    )
    assert old2 in content, "Neither pattern found"
    content = content.replace(old2, new2, 1)
    print("Title filter added to rebuilt scraper")

ast.parse(content)
print("Syntax OK")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
