import re

with open('/Users/alexdakers/meridian-server/NOTES.md', 'r') as f:
    content = f.read()

# Update header
old_header = "Last updated: 14 April 2026 (Session 54 — VPS push overhaul, FA scraper rebuild, Last Scraped fix)"
new_header = "Last updated: 15 April 2026 (Session 55 — AI pick fixes, backfill 38 missed articles)"
content = content.replace(old_header, new_header, 1)

# Update DB counts
old_db = """## Database (14 April 2026 — end of session 54)
| Source | Mac | VPS |
|---|---|---|
| FT | ~248 | ~248 |
| Economist | ~327 | ~327 |
| FA | ~144 | ~144 |
| Bloomberg | ~45 | ~45 |
| Other | ~46 | ~46 |
| **Total** | **~810** | **~810** |

AI picks in Feed (auto_saved=1): ~68
API balance: ~$9"""

new_db = """## Database (15 April 2026 — end of session 55)
| Source | Mac | VPS |
|---|---|---|
| FT | ~286 | ~286 |
| Economist | ~327 | ~327 |
| FA | ~159 | ~159 |
| Bloomberg | ~45 | ~45 |
| Other | ~46 | ~46 |
| **Total** | **~863** | **~863** |

AI picks in Feed (auto_saved=1): ~106 (38 backfilled this session)
API balance: check console.anthropic.com"""

content = content.replace(old_db, new_db, 1)

# Update outstanding issues
old_issues = """### 🔴 Session 55 — do first
1. **FA AI picks missing pub_date** — add pub_date to Sonnet scoring prompt response for FA articles
2. **Economist delivery gaps** — 3 zero-days (04-08, 04-11, 04-13); check bookmarks scraper logs + session health
3. **FT 13 unenriched articles** — check enrichment pipeline, may need manual trigger

### 🔴 Priority fixes
4. Economist scraper: add login-redirect detection — fail gracefully, don't hang
5. FA cookie renewal — expires 2026-05-23
6. eco_playwright_profile — continue building browsing history for Economist feed access

### 🟡 Planned Features
7. Daily briefing backend
8. Chat Q&A"""

new_issues = """### 🔴 Session 56 — do first
1. **FA AI picks missing pub_date** — add pub_date to Sonnet scoring prompt response for FA articles
2. **Economist delivery gaps** — 3 zero-days (04-08, 04-11, 04-13); check bookmarks scraper logs + session health
3. **FT 13 unenriched articles** — check enrichment pipeline, may need manual trigger
4. **API credit indicator** — no programmatic endpoint; consider failure-rate proxy in stats panel

### 🔴 Priority fixes
5. Economist scraper: add login-redirect detection — fail gracefully, don't hang
6. FA cookie renewal — expires 2026-05-23
7. eco_playwright_profile — still Cloudflare-blocked; continue building browsing history

### 🟡 Planned Features
8. Daily briefing backend
9. Chat Q&A"""

content = content.replace(old_issues, new_issues, 1)

# Add session 55 to build history
old_history = "### 14 April 2026 (Session 54)"
new_session = """### 15 April 2026 (Session 55)

**Core achievements:** AI pick pipeline fixes, 38-article backfill, model retirement update

**AI pick fixes (all deployed)**
- Root cause of 0 scores: `max_tokens: 2000` too low for 100+ candidates — Sonnet was cut off mid-JSON array
  Fix: `max_tokens: 2000` → `6000`
- Root cause of timeout: 105 candidates in one call, connection dropped after 16 mins
  Fix: `timeout: 60` → `120`; candidates capped at 50 newest
- Root cause of high candidate count: no pub_date filter — articles accumulated over multiple days
  Fix: filter candidates to last 36h pub_date (pass-through blank pub_dates for FA)
- Root cause of midday gate blocking: `hour < 12` caught the 11:40 trigger at 11:47
  Fix: `hour < 12` → `hour < 13`, giving 1h buffer
- Scoring threshold: `>= 9` → `>= 8` to widen output on quieter news days
- Economist playwright profile: still Cloudflare-blocked ("Just a moment..." on both feed URLs)

**Backfill**
- Ran `backfill_ai_picks.py` against last 14 days of FT feed
- 126 candidates scored in 3 batches of 50
- 38 saved to Feed (score >=8), 54 to Suggested (score 6-7)
- Pushed to VPS via vps_push.py
- Notable picks: Iran war/ceasefire articles, Fed energy debate, Wall Street trading boom,
  Anthropic cyber risk, Gates of Hormuz, dollar weakness, China export controls

**Model retirement fix**
- All 7 instances of `claude-sonnet-4-20250514` in meridian.html updated to `claude-sonnet-4-6`
- Retirement date: June 15 2026
- server.py was already using current model strings

**`/api/dev/restart` endpoint**
- New endpoint: spawns new Flask process in detached thread, then exits
- Shell bridge gets response before old process dies → clean restart without losing bridge
- Prevents launchd throttle loop that plagued session 54

**DB counts: ~863 articles (286 FT, 327 Eco, 159 FA, 45 Bloomberg, 46 other)**

### 14 April 2026 (Session 54)"""

content = content.replace(old_history, new_session, 1)

with open('/Users/alexdakers/meridian-server/NOTES.md', 'w') as f:
    f.write(content)
print("NOTES.md updated")
