with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    content = f.read()

old = 'class="btn btn-dark" style="font-size:11px;padding:4px 10px" id="save-sug-'
new = 'class="btn btn-outline" style="font-size:11px;padding:4px 10px;color:var(--accent);border-color:var(--accent);font-weight:600" id="save-sug-'

assert old in content, "Not found"
content = content.replace(old, new, 1)

count = content.count('<html lang')
assert count == 1, f"html lang count: {count}"

with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(content)

with open('/Users/alexdakers/meridian-server/logs/btn_patch.txt', 'w') as f:
    f.write(f"Done. html lang count: {count}\n")
print("Done")
