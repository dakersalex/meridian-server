with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    content = f.read()

# Fix 1: feed-controls-inner should use display:contents so children participate in flex
old_fc = '<span class="feed-controls-inner" style="display:contents">'
new_fc = '<span class="feed-controls-inner" style="display:contents;flex:none">'

# Actually display:contents is the right approach but computed shows block
# The real issue: when we restore with style.display='' it removes the inline style
# but doesn't restore display:contents (which is non-standard inheritance)
# Better: don't use a wrapper span at all — just use a flag class and hide children

# Simpler fix: remove feed-controls-inner span entirely, just hide/show individual 
# feed filter selects and FILTER label by targeting .feed-controls class elements

# Actually simplest fix: just ensure feed-actions-bar restores as flex not block
old_feed_restore = (
    "const fab=document.getElementById('feed-actions-bar');if(fab)fab.style.display='';"
)
new_feed_restore = (
    "const fab=document.getElementById('feed-actions-bar');if(fab)fab.style.display='flex';"
)
assert old_feed_restore in content, "fab restore not found"
content = content.replace(old_feed_restore, new_feed_restore, 1)
print("Fix 1: fab restores as flex")

# Fix 2: feed-controls-inner — use display:contents which passes flex to children
# but when restoring it also needs to be display:contents not block
old_fc_restore = (
    "const fc=fho.querySelector('.feed-controls-inner');if(fc)fc.style.display='';"
)
new_fc_restore = (
    "const fc=fho.querySelector('.feed-controls-inner');if(fc)fc.style.display='contents';"
)
assert old_fc_restore in content, "fc restore not found"
content = content.replace(old_fc_restore, new_fc_restore, 1)
print("Fix 2: fc restores as contents")

count = content.count('<html lang')
assert count == 1
with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(content)
print(f"Done. html lang: {count}")
