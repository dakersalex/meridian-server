with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    content = f.read()

old = (
    '    renderSuggestedHeader(area, newCount);\n'
    '    if (!suggestedArticles.length) {\n'
    '      area.innerHTML += \'<div class="empty-state">'
)
new = (
    '    renderSuggestedHeader(area, newCount);\n'
    '    area.innerHTML = \'\'; // clear loading message now header is in fho\n'
    '    if (!suggestedArticles.length) {\n'
    '      area.innerHTML += \'<div class="empty-state">'
)

assert old in content, "Pattern not found"
content = content.replace(old, new, 1)

count = content.count('<html lang')
assert count == 1
with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(content)
print(f"Done. html lang: {count}")
