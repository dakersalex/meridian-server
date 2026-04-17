with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    content = f.read()

# Add an id to the Stats/Bloomberg div so we can target it
old_stats_div = '<div style="margin-left:auto;display:flex;align-items:center;gap:6px">'
new_stats_div = '<div id="feed-actions-bar" style="margin-left:auto;display:flex;align-items:center;gap:6px">'
assert old_stats_div in content, "stats div not found"
content = content.replace(old_stats_div, new_stats_div, 1)
print("Fix 1: id added to stats/bloomberg div")

# Hide feed-actions-bar when switching to Suggested
old_suggested_view = (
    "const sd=document.getElementById('suggested-filter-bar');"
    "if(sd)sd.remove();"
    "const fc=fho.querySelector('.feed-controls-inner');"
    "if(fc)fc.style.display='';"
)

# In setView suggested — hide feed-actions-bar
old_sug_mode = (
    "if(fho){fho.style.display='flex';fho.dataset.mode='suggested';}"
)
new_sug_mode = (
    "if(fho){fho.style.display='flex';fho.dataset.mode='suggested';"
    "const fab=document.getElementById('feed-actions-bar');if(fab)fab.style.display='none';}"
)
assert old_sug_mode in content, "sug mode not found"
content = content.replace(old_sug_mode, new_sug_mode, 1)
print("Fix 2: hide feed-actions-bar on Suggested")

# Restore feed-actions-bar when switching back to Feed
old_feed_restore = (
    "const sd=document.getElementById('suggested-filter-bar');if(sd)sd.remove();"
    "const fc=fho.querySelector('.feed-controls-inner');if(fc)fc.style.display='';"
)
new_feed_restore = (
    "const sd=document.getElementById('suggested-filter-bar');if(sd)sd.remove();"
    "const fc=fho.querySelector('.feed-controls-inner');if(fc)fc.style.display='';"
    "const fab=document.getElementById('feed-actions-bar');if(fab)fab.style.display='';"
)
assert old_feed_restore in content, "feed restore not found"
content = content.replace(old_feed_restore, new_feed_restore, 1)
print("Fix 3: restore feed-actions-bar on Feed")

count = content.count('<html lang')
assert count == 1
with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(content)
print(f"Done. html lang: {count}")
