
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# ── 1. Top topics: slice(0,7) → slice(0,5)
old_topics = "const topicSorted = Object.entries(topicCounts).sort((a,b)=>b[1]-a[1]).slice(0,7);"
new_topics = "const topicSorted = Object.entries(topicCounts).sort((a,b)=>b[1]-a[1]).slice(0,5);"
if old_topics in html:
    html = html.replace(old_topics, new_topics)
    results.append('topics slice 5: OK')
else:
    results.append('topics slice: NOT FOUND')

# ── 2. Fix 24h: pub_date is "2026-04-03" (no time), compare date strings not timestamps
# Today's date string vs pub_date string comparison
old_24h = "      const cutoff = Date.now() - 24*60*60*1000;\n      const recent = allArts.filter(a => new Date(a.pub_date||a.saved_at).getTime() > cutoff);"
new_24h = """      // pub_date is date-only (YYYY-MM-DD), compare as string to today and yesterday
      const now = new Date();
      const todayStr = now.toISOString().slice(0,10);
      const yd = new Date(now - 24*60*60*1000);
      const yestStr = yd.toISOString().slice(0,10);
      const recent = allArts.filter(a => {
        if(a.pub_date) return a.pub_date >= yestStr;
        // fallback: saved_at timestamp
        return new Date(a.saved_at).getTime() > (Date.now() - 24*60*60*1000);
      });"""
if old_24h in html:
    html = html.replace(old_24h, new_24h)
    results.append('24h date fix: OK')
else:
    results.append('24h fix: NOT FOUND')

# ── 3. Left alignment — folder-switcher nav tabs have padding making them
# appear inset vs the masthead logo. Reduce folder-switcher left padding to match.
# Currently: padding: 8px 20px (from CSS)
# Masthead has: padding: 14px 20px  — both are 20px, so alignment is correct.
# The issue in the screenshot is that the nav dot + "News Feed" text appears
# indented because the folder-tab has internal left padding.
# Fix: reduce padding on folder-switcher from 8px 20px to 8px 16px
# and reduce folder-tab internal padding to align with logo baseline
old_fs_pad = '''#folder-switcher {
  background: var(--paper-2);
  padding: 8px 20px;'''
new_fs_pad = '''#folder-switcher {
  background: var(--paper-2);
  padding: 8px 20px 8px 18px;'''
if old_fs_pad in html:
    html = html.replace(old_fs_pad, new_fs_pad)
    results.append('folder-switcher padding: OK')
else:
    results.append('folder-switcher padding: NOT FOUND')

# Also fix the folder-tab so active tab "News Feed" dot aligns with logo M
old_ftab = '.folder-tab { display: flex; align-items: center; gap: 6px; padding: 5px 13px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; white-space: nowrap; background: none; border: none; font-family: \'IBM Plex Sans\', sans-serif; color: var(--ink-3); transition: all 0.15s; }'
new_ftab = '.folder-tab { display: flex; align-items: center; gap: 6px; padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; white-space: nowrap; background: none; border: none; font-family: \'IBM Plex Sans\', sans-serif; color: var(--ink-3); transition: all 0.15s; }'
if old_ftab in html:
    html = html.replace(old_ftab, new_ftab)
    results.append('folder-tab padding: OK')
else:
    results.append('folder-tab: NOT FOUND')

# Also fix main-nav left padding to align sub-nav tabs with logo
old_main_nav = '.main-nav { border-bottom: 1px solid var(--rule); padding: 0 20px;'
new_main_nav = '.main-nav { border-bottom: 1px solid var(--rule); padding: 0 20px 0 18px;'
if old_main_nav in html:
    html = html.replace(old_main_nav, new_main_nav)
    results.append('main-nav padding: OK')
else:
    results.append('main-nav padding: NOT FOUND')

# Fix filter row alignment too
old_fh = 'display:flex;align-items:center;gap:8px;padding:7px 20px;background:var(--paper-2);border-bottom:2px solid var(--rule);position:sticky;top:147px;z-index:52;isolation:isolate;'
new_fh = 'display:flex;align-items:center;gap:8px;padding:7px 20px 7px 18px;background:var(--paper-2);border-bottom:2px solid var(--rule);position:sticky;top:147px;z-index:52;isolation:isolate;'
if old_fh in html:
    html = html.replace(old_fh, new_fh)
    results.append('filter row padding: OK')
else:
    results.append('filter row: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
