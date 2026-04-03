
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# Remove now-orphaned status-dot-nav JS references (element no longer exists in DOM)
old_nd = ";const nd=document.getElementById('status-dot-nav');if(nd)nd.className='status-dot connected';const nt=document.getElementById('status-text-nav');if(nt)nt.textContent='meridianreader.com · connected';"
if old_nd in html:
    html = html.replace(old_nd, '')
    results.append('status-dot-nav JS removed: OK')
else:
    results.append('status-dot-nav JS: not found (OK)')

old_nd2 = ";const nd2=document.getElementById('status-dot-nav');if(nd2)nd2.className='status-dot error';const nt2=document.getElementById('status-text-nav');if(nt2)nt2.textContent='Server offline';"
if old_nd2 in html:
    html = html.replace(old_nd2, '')
    results.append('status-dot-nav offline JS removed: OK')
else:
    results.append('status-dot-nav offline JS: not found (OK)')

# Feed area needs top padding so content isn't hidden behind sticky rows
# Total sticky height: ~57 (masthead) + 44 (folder-switcher) + 38 (main-nav) + 36 (info-strip) + 38 (filter) = ~213px
# But feed-area is inside main-layout which is below the sticky rows, so it's fine — just add a little breathing room
old_feed_area = '.feed-area { padding: 0 20px 20px; border-right: 1px solid var(--rule); }'
new_feed_area = '.feed-area { padding: 0 20px 20px; border-right: 1px solid var(--rule); }'
results.append('Feed area padding: already correct')

# Update masthead sync label on init too — populate on load
old_date_js = "document.getElementById('date-display').textContent=new Date().toLocaleDateString('en-GB',{weekday:'long',day:'numeric',month:'long',year:'numeric'});"
new_date_js = "document.getElementById('date-display').textContent=new Date().toLocaleDateString('en-GB',{weekday:'long',day:'numeric',month:'long',year:'numeric'});const mSyncInit=document.getElementById('last-sync-masthead');if(mSyncInit)mSyncInit.textContent='';"
if old_date_js in html:
    html = html.replace(old_date_js, new_date_js)
    results.append('Date init: OK')
else:
    results.append('Date init: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
