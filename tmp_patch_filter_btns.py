with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    html = f.read()

# 1. Remove stats-toggle-btn from folder-switcher
old_stats_btn = '    <button id="stats-toggle-btn" onclick="toggleStatsStrip()" style="font-size:11px;padding:4px 10px;background:transparent;border:1px solid rgba(0,0,0,0.2);color:var(--ink-2);border-radius:4px;cursor:pointer;font-family:inherit;display:flex;align-items:center;gap:5px;">📊 Stats</button>\n'
assert html.count(old_stats_btn) == 1, f"stats-toggle-btn count: {html.count(old_stats_btn)}"
html = html.replace(old_stats_btn, '')

# 2. Remove clip-bbg-btn from folder-switcher
old_clip_btn = '    <button class="btn btn-outline" onclick="clipBloomberg()" id="clip-bbg-btn" style="font-size:10px;padding:3px 7px;display:none">📎 Clip Bloomberg</button>\n'
assert html.count(old_clip_btn) == 1, f"clip-bbg-btn count: {html.count(old_clip_btn)}"
html = html.replace(old_clip_btn, '')

# 3. Insert Stats + Clip Bloomberg buttons into filter row, right before the select-all-btn
old_anchor = '  <button class="btn btn-outline" onclick="selectAll()" style="font-size:11px;padding:4px 8px;display:none" id="select-all-btn">Select all</button>'
assert html.count(old_anchor) == 1, f"select-all-btn count: {html.count(old_anchor)}"
new_anchor = (
    '  <div style="margin-left:auto;display:flex;align-items:center;gap:6px">\n'
    '    <button id="stats-toggle-btn" onclick="toggleStatsStrip()" style="font-size:11px;padding:4px 10px;background:transparent;border:1px solid rgba(0,0,0,0.2);color:var(--ink-2);border-radius:4px;cursor:pointer;font-family:inherit;display:flex;align-items:center;gap:5px;">📊 Stats</button>\n'
    '    <button class="btn btn-outline" onclick="clipBloomberg()" id="clip-bbg-btn" style="font-size:10px;padding:3px 7px;display:none">📎 Clip Bloomberg</button>\n'
    '  </div>\n'
    '  <button class="btn btn-outline" onclick="selectAll()" style="font-size:11px;padding:4px 8px;display:none" id="select-all-btn">Select all</button>'
)
html = html.replace(old_anchor, new_anchor)

with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(html)

print("Patch applied OK")
# Verify no duplicate html tags
count = html.count('<html lang')
print(f"<html lang count: {count} (expected 1)")
