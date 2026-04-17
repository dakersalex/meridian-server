with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    content = f.read()

old = (
    "    let params = '';\n"
    "    if (suggestedSince) params += '&since=' + suggestedSince;\n"
    "    if (suggestedStatus !== 'all') params += '&status=' + suggestedStatus;\n"
    "    if (suggestedSource) params += '&source=' + encodeURIComponent(suggestedSource);\n"
    "    const r = await fetch(SERVER + '/api/suggested?' + params);"
)
new = (
    "    let params = '';\n"
    "    if (suggestedSince) params += '&since=' + suggestedSince;\n"
    "    if (suggestedStatus !== 'all') params += '&status=' + suggestedStatus;\n"
    "    if (suggestedSource) params += '&source=' + encodeURIComponent(suggestedSource);\n"
    "    if (suggestedSort) params += '&sort=' + suggestedSort;\n"
    "    const r = await fetch(SERVER + '/api/suggested?' + params);"
)

assert old in content, "Not found"
content = content.replace(old, new, 1)

count = content.count('<html lang')
assert count == 1
with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(content)
print(f"Done. html lang: {count}")
