with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    content = f.read()

# The fix: in setView feed restore, reset fho.dataset.mode BEFORE renderFeed
# and clear the suggested filter bar from fho by restoring feed controls visibility
# The real issue: renderSuggestedHeader replaces fho.innerHTML entirely
# Solution: store original fho HTML and restore it on switch back

# Change renderSuggestedHeader to use a child div instead of replacing fho.innerHTML
old_header_fn = (
    "function renderSuggestedHeader(area, newCount) {\n"
    "  const fho = document.getElementById('feed-header-outer');\n"
    "  if (fho && fho.dataset.mode === 'suggested') {\n"
    "    // Render filter bar into sticky header\n"
    "    area = fho;\n"
    "  }\n"
)
new_header_fn = (
    "function renderSuggestedHeader(area, newCount) {\n"
    "  const fho = document.getElementById('feed-header-outer');\n"
    "  if (fho && fho.dataset.mode === 'suggested') {\n"
    "    // Hide feed controls, show suggested controls in fho\n"
    "    const feedControls = fho.querySelector('.feed-controls-inner');\n"
    "    if (feedControls) feedControls.style.display = 'none';\n"
    "    let sugDiv = document.getElementById('suggested-filter-bar');\n"
    "    if (!sugDiv) { sugDiv = document.createElement('div'); sugDiv.id = 'suggested-filter-bar'; sugDiv.style.cssText='display:flex;align-items:center;gap:8px;flex:1;flex-wrap:nowrap;'; fho.appendChild(sugDiv); }\n"
    "    area = sugDiv;\n"
    "  }\n"
)
assert old_header_fn in content, "Header fn not found"
content = content.replace(old_header_fn, new_header_fn, 1)
print("Fix 1: renderSuggestedHeader uses child div")

# Wrap existing feed controls in feed-header-outer with a class for targeting
old_fho_inner = (
    '<span style="font-size:10px;font-weight:500;letter-spacing:0.8px;'
    'text-transform:uppercase;color:var(--ink-3);margin-right:4px">Filter</span>'
)
new_fho_inner = (
    '<span class="feed-controls-inner" style="display:contents">'
    '<span style="font-size:10px;font-weight:500;letter-spacing:0.8px;'
    'text-transform:uppercase;color:var(--ink-3);margin-right:4px">Filter</span>'
)
assert old_fho_inner in content, "fho inner not found"
content = content.replace(old_fho_inner, new_fho_inner, 1)
print("Fix 2: wrapped feed controls in feed-controls-inner span")

# Close the feed-controls-inner span before the Bloomberg/Stats buttons div
old_close_span = '<div style="margin-left:auto;display:flex;align-items:center;gap:6px">'
new_close_span = '</span><div style="margin-left:auto;display:flex;align-items:center;gap:6px">'
assert old_close_span in content, "close span not found"
content = content.replace(old_close_span, new_close_span, 1)
print("Fix 3: closed feed-controls-inner before Stats/Bloomberg")

# On switch back to Feed: remove suggested-filter-bar and show feed-controls-inner
old_feed_restore = (
    "if(fho){fho.style.display='flex';fho.dataset.mode='feed';}renderFeed();"
)
new_feed_restore = (
    "if(fho){fho.style.display='flex';fho.dataset.mode='feed';"
    "const sd=document.getElementById('suggested-filter-bar');if(sd)sd.remove();"
    "const fc=fho.querySelector('.feed-controls-inner');if(fc)fc.style.display='';"
    "}renderFeed();"
)
assert old_feed_restore in content, "feed restore not found"
content = content.replace(old_feed_restore, new_feed_restore, 1)
print("Fix 4: feed restore removes suggested bar, shows feed controls")

# Also fix isFho check — area is now sugDiv not fho
old_is_fho = "  const isFho = area === document.getElementById('feed-header-outer');\n"
new_is_fho = "  const isFho = area && area.id === 'suggested-filter-bar';\n"
assert old_is_fho in content, "isFho not found"
content = content.replace(old_is_fho, new_is_fho, 1)
print("Fix 5: isFho check updated")

count = content.count('<html lang')
assert count == 1, f"html lang: {count}"
with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(content)
print(f"Done. html lang: {count}")
