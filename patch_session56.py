with open('/Users/alexdakers/meridian-server/NOTES.md', 'r') as f:
    content = f.read()

old = "### 16 April 2026 (Session 56)"
new = """### 17 April 2026 (Session 57)

**Suggested tab UI overhaul**
- Feed filter bar (feed-header-outer) now hides on Suggested/Newsletters/Interviews tabs
- Suggested filter bar moved into sticky feed-header-outer slot (same bg, border, position)
- Sort toggle added: ★ Score / 📅 Date — server-side ORDER BY pub_date DESC or score DESC
- sort param now passed correctly in renderSuggested fetch call (was missing)
- Save to Feed button: btn-dark → btn-outline with accent colour
- Card padding-bottom:14px added for spacing

**Suggested date fixes**
- formatPubDate() now used for all Suggested cards (was raw pub_date string)
- formatPubDate() fallback: saved_at||added_at (suggested articles have added_at not saved_at)
- All non-YYYY-MM-DD pub_dates normalised on VPS (66 + 0 fixed)
- _norm_date() added to save_suggested_snapshot() — all future inserts store YYYY-MM-DD
- Backfilled pub_dates from articles table: 36 Mac, 34 VPS
- Feed filter bar: flex-wrap:nowrap so Stats/Bloomberg stay on same line

**Suggested sync**
- /api/push-suggested endpoint added to server.py
- vps_push.py now pushes suggested_articles (48h window) after every sync
- Full historical backfill: pushed all Mac suggested → VPS (263 total on VPS)

**FA scoring fixes**
- FA ≥7 → Feed threshold: promoted 3 remaining articles from VPS suggested
- /podcasts/ added to FA SKIP_PREFIXES (podcast article was in Feed)
- Deleted podcast article from VPS Feed

**AI pick pipeline confirmed working**
- 17 Apr 06:04 run: 32 candidates → 32 scores → 4 Feed, 17 Suggested ✅
- Sonnet scored exactly N candidates (filter-before-prompt fix working)

**DB counts: ~906 articles, 263 suggested on VPS**

### 16 April 2026 (Session 56)"""

content = content.replace(old, new, 1)

# Update outstanding issues
old_issues = """### 🔴 Session 57 — do first
1. **Economist delivery gaps** — zero-days on 04-08, 04-11, 04-13; check bookmarks scraper logs
2. **FT unenriched backlog** — 59 pending title_only articles; trigger enrichment run
3. **Feed filter bar visible on Suggested tab** — `.feed-controls` hide logic exists but top filter row still shows; needs DOM inspection to find correct element to hide
4. **API credit indicator** — consider failure-rate proxy in stats panel
5. **wake_and_sync.sh push redundancy** — Flask auto-pushes now; explicit vps_push.py call redundant for articles"""

new_issues = """### 🔴 Session 58 — do first
1. **Economist delivery gaps** — zero-days on 04-08, 04-11, 04-13; check bookmarks scraper logs
2. **FT unenriched backlog** — 59+ pending title_only articles; trigger enrichment run
3. **API credit indicator** — consider failure-rate proxy in stats panel
4. **wake_and_sync.sh push redundancy** — Flask auto-pushes now; explicit vps_push.py call redundant for articles"""

content = content.replace(old_issues, new_issues, 1)

with open('/Users/alexdakers/meridian-server/NOTES.md', 'w') as f:
    f.write(content)
print("NOTES.md updated")
