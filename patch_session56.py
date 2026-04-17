with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    content = f.read()

# Fix setView('suggested') and setView('interviews') to also hide feed-header-outer
old_suggested = "else if(view==='suggested'){const controls=document.querySelector('.feed-controls');const counter=document.getElementById('feed-counter');if(controls)controls.style.display='none';if(counter)counter.style.display='none';renderSuggested(true);}"
new_suggested = "else if(view==='suggested'){const controls=document.querySelector('.feed-controls');const counter=document.getElementById('feed-counter');const fho=document.getElementById('feed-header-outer');if(controls)controls.style.display='none';if(counter)counter.style.display='none';if(fho)fho.style.display='none';renderSuggested(true);}"

assert old_suggested in content, "Suggested view pattern not found"
content = content.replace(old_suggested, new_suggested, 1)
print("Suggested hide fix applied")

# Also fix interviews view
old_interviews = "else if(view==='interviews'){const controls=document.querySelector('.feed-controls');const counter=document.getElementById('feed-counter');if(controls)controls.style.display='none';if(counter)counter.style.display='none';renderInterviews();}"
new_interviews = "else if(view==='interviews'){const controls=document.querySelector('.feed-controls');const counter=document.getElementById('feed-counter');const fho=document.getElementById('feed-header-outer');if(controls)controls.style.display='none';if(counter)counter.style.display='none';if(fho)fho.style.display='none';renderInterviews();}"

assert old_interviews in content, "Interviews view pattern not found"
content = content.replace(old_interviews, new_interviews, 1)
print("Interviews hide fix applied")

# Also fix newsletters view if it exists
if "view==='newsletters'" in content:
    old_newsletters = "if(view==='newsletters'){renderNewsletters();}"
    new_newsletters = "if(view==='newsletters'){const fho=document.getElementById('feed-header-outer');if(fho)fho.style.display='none';renderNewsletters();}"
    if old_newsletters in content:
        content = content.replace(old_newsletters, new_newsletters, 1)
        print("Newsletters hide fix applied")

# Restore feed-header-outer when switching back to feed
old_feed = "else{const controls=document.querySelector('.feed-controls');const counter=document.getElementById('feed-counter');if(controls)controls.style.display='';if(counter)counter.style.display='';renderFeed();}"
new_feed = "else{const controls=document.querySelector('.feed-controls');const counter=document.getElementById('feed-counter');const fho=document.getElementById('feed-header-outer');if(controls)controls.style.display='';if(counter)counter.style.display='';if(fho)fho.style.display='';renderFeed();}"

assert old_feed in content, "Feed restore pattern not found"
content = content.replace(old_feed, new_feed, 1)
print("Feed restore fix applied")

count = content.count('<html lang')
assert count == 1
with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(content)
print(f"Done (html lang count: {count})")
