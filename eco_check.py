with open('/Users/alexdakers/meridian-server/meridian.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove Enrich All button
old_btn = '<button class="btn btn-outline" onclick="enrichViaBrowser()" id="enrich-btn" style="font-size:10px;padding:4px 10px;">Enrich All</button>\n    '
assert old_btn in content, "Button not found"
content = content.replace(old_btn, '', 1)
print("Button removed")

# 2. Remove enrichViaBrowser JS function
# It starts at 'async function enrichViaBrowser(){' and ends just before 'async function syncAll(){'
JS_START = 'async function enrichViaBrowser(){'
JS_END   = 'async function syncAll(){'
idx_s = content.find(JS_START)
idx_e = content.find(JS_END)
assert idx_s > 0 and idx_e > idx_s, f"JS not found: {idx_s} {idx_e}"
removed_js = content[idx_s:idx_e]
content = content[:idx_s] + content[idx_e:]
print(f"JS function removed ({len(removed_js.splitlines())} lines)")

assert content.count('<html lang') == 1
with open('/Users/alexdakers/meridian-server/meridian.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("meridian.html done")
