with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    content = f.read()

# Fix 2: Suggested filter bar — render into feed-header-outer (sticky, same bg)
# When setView('suggested'), instead of hiding feed-header-outer, swap its contents
# and restore on switch back

old_suggested_view = (
    "else if(view==='suggested'){"
    "const controls=document.querySelector('.feed-controls');"
    "const counter=document.getElementById('feed-counter');"
    "const fho=document.getElementById('feed-header-outer');"
    "if(controls)controls.style.display='none';"
    "if(counter)counter.style.display='none';"
    "if(fho)fho.style.display='none';"
    "renderSuggested(true);}"
)
new_suggested_view = (
    "else if(view==='suggested'){"
    "const controls=document.querySelector('.feed-controls');"
    "const counter=document.getElementById('feed-counter');"
    "const fho=document.getElementById('feed-header-outer');"
    "if(controls)controls.style.display='none';"
    "if(counter)counter.style.display='none';"
    "if(fho){fho.style.display='flex';fho.dataset.mode='suggested';}"
    "renderSuggested(true);}"
)
assert old_suggested_view in content, "Suggested view not found"
content = content.replace(old_suggested_view, new_suggested_view, 1)
print("Suggested view mode flag: applied")

# Restore feed-header-outer to feed mode when switching back
old_feed_restore = (
    "else{const controls=document.querySelector('.feed-controls');"
    "const counter=document.getElementById('feed-counter');"
    "const fho=document.getElementById('feed-header-outer');"
    "if(controls)controls.style.display='';"
    "if(counter)counter.style.display='';"
    "if(fho)fho.style.display='';"
    "renderFeed();}"
)
new_feed_restore = (
    "else{const controls=document.querySelector('.feed-controls');"
    "const counter=document.getElementById('feed-counter');"
    "const fho=document.getElementById('feed-header-outer');"
    "if(controls)controls.style.display='';"
    "if(counter)counter.style.display='';"
    "if(fho){fho.style.display='flex';fho.dataset.mode='feed';}"
    "renderFeed();}"
)
assert old_feed_restore in content, "Feed restore not found"
content = content.replace(old_feed_restore, new_feed_restore, 1)
print("Feed restore: applied")

# Fix 3: renderSuggestedHeader — render into feed-header-outer instead of area
# Change renderSuggestedHeader to target fho if available
old_header_fn = "function renderSuggestedHeader(area, newCount) {"
new_header_fn = (
    "function renderSuggestedHeader(area, newCount) {\n"
    "  const fho = document.getElementById('feed-header-outer');\n"
    "  if (fho && fho.dataset.mode === 'suggested') {\n"
    "    // Render filter bar into sticky header\n"
    "    area = fho;\n"
    "  }\n"
)
assert old_header_fn in content, "Header fn not found"
content = content.replace(old_header_fn, new_header_fn, 1)
print("renderSuggestedHeader redirect: applied")

# Fix 4: renderSuggestedHeader output — change area.innerHTML to not clobber the whole area
# The function does area.innerHTML = '<div...>' which would wipe the feed controls in fho
# We need it to set fho's innerHTML to just the filter content (no wrapping div needed since fho is already the bar)
old_area_html = (
    "  area.innerHTML = '<div style=\"display:flex;align-items:center;gap:8px;margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid var(--rule);flex-wrap:wrap\">'"
)
new_area_html = (
    "  const isFho = area === document.getElementById('feed-header-outer');\n"
    "  const wrapStart = isFho ? '' : '<div style=\"display:flex;align-items:center;gap:8px;margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid var(--rule);flex-wrap:wrap\">';\n"
    "  const wrapEnd = isFho ? '' : '</div>';\n"
    "  area.innerHTML = wrapStart"
)
assert old_area_html in content, "area.innerHTML not found"
content = content.replace(old_area_html, new_area_html, 1)
print("area.innerHTML wrap: applied")

# Fix the closing of the innerHTML concatenation
old_close = (
    "    + '</div>'\n"
    "    + '<div id=\"sug-bulk-bar\""
)
new_close = (
    "    + wrapEnd\n"
    "    + '<div id=\"sug-bulk-bar\""
)
assert old_close in content, "Close div not found"
content = content.replace(old_close, new_close, 1)
print("Close div: applied")

count = content.count('<html lang')
assert count == 1, f"html lang: {count}"
with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(content)
print(f"Done (html lang: {count})")
