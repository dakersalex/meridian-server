with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    content = f.read()

old = "      const pubDateDisplay = a.pub_date ? a.pub_date : new Date().toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'});"
new = "      const pubDateDisplay = formatPubDate(a);"

assert old in content, "Pattern not found"
content = content.replace(old, new, 1)

count = content.count('<html lang')
assert count == 1
with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(content)
print(f"Done. html lang: {count}")
