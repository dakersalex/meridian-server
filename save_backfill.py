import re

with open('/Users/alexdakers/meridian-server/NOTES.md', 'r') as f:
    content = f.read()

# Update header
content = content.replace(
    "Last updated: 15 April 2026 (Session 55 — AI pick fixes, backfill, JSON scoring overhaul)",
    "Last updated: 15 April 2026 (Session 55 — AI pick fixes, FA scraper overhaul, auto VPS push)"
)

# Update FA scraper section
old_fa = """## Foreign Affairs Scraper (rebuilt Session 54)

### Architecture
- Playwright, fa_profile/, headless=True
- FA cookie expires 2026-05-23
- Three sources per run:
  1. **Saved articles** — `/my-foreign-affairs/saved-articles`
  2. **Latest two issues** — dynamically discovered from `/issues` landing page (not hardcoded)
  3. **Most-read** — `foreignaffairs.com/most-read`
- Uses `h3 a` CSS selector to extract article links (consistent across all FA pages)
- SKIP_PREFIXES includes `/book-reviews/` to exclude review index pages

### Why old scraper failed
- Had 3 hardcoded issue URLs that were never updated → all articles already in DB → 0 new every run

### pub_date status
- 144 FA articles, 141 have correct pub_dates
- 3 blanks were AI pick articles (saved_at used as fallback in swim lanes)
- Swim lane fallback: frontend uses `saved_at` when `pub_date` missing/invalid → articles appear on scrape date not pub date"""

new_fa = """## Foreign Affairs Scraper (rebuilt Session 54, overhauled Session 55)

### Architecture
- Playwright, fa_profile/, headless=True
- FA cookie expires 2026-05-23
- Two sources per run:
  1. **Saved articles** — `/my-foreign-affairs/saved-articles` (every run)
  2. **Latest issue only** — dynamically discovered from `/issues`; skipped if URL matches `fa_last_issue_url` in kt_meta (FA publishes every ~2 months — no need to scrape unchanged issue twice daily)
- Most-read **removed from scraper** — handled exclusively by AI pick pipeline to avoid bypassing quality scoring
- Uses `h3 a` CSS selector to extract article links
- SKIP_PREFIXES includes `/book-reviews/`; title blocklist includes "Recent Books"

### Issue watermark
- `fa_last_issue_url` stored in kt_meta after each issue scrape
- Next run compares current latest issue URL; skips if unchanged
- Resets automatically when FA publishes new issue

### pub_date status
- 159 FA articles, all correctly dated
- Swim lane fallback: frontend uses `saved_at` when `pub_date` missing/invalid"""

content = content.replace(old_fa, new_fa, 1)

# Update VPS push architecture section
old_vps = """### New behaviour
- `vps_push.py` — standalone script, called from wake_and_sync.sh
- Reads `last_push_ts` watermark from kt_meta → only pushes articles newer than that
- Always pushes last 48h to catch enrichment updates on recently saved articles
- After article push, explicitly pushes `last_sync_ft/economist/fa` to VPS via `/api/push-meta`
- Normal syncs: ~5-20 articles pushed instead of 771
- New `/api/push-meta` endpoint on server.py (both Mac + VPS) — upserts kt_meta key-value pairs"""

new_vps = """### New behaviour
- `vps_push.py` — standalone script, called from wake_and_sync.sh AND automatically after every `/api/sync`
- Reads `last_push_ts` watermark from kt_meta → only pushes articles newer than that
- Always pushes last 48h to catch enrichment updates on recently saved articles
- After article push, explicitly pushes `last_sync_ft/economist/fa` to VPS via `/api/push-meta`
- Normal syncs: ~5-20 articles pushed instead of 771
- New `/api/push-meta` endpoint on server.py (both Mac + VPS) — upserts kt_meta key-value pairs

### Auto-push after every sync (Session 55)
- `_enrich_after_sync()` in Flask now calls `vps_push.py` as subprocess after enrichment completes
- Applies to ALL sync triggers: launchd schedule, UI "Sync all" button, direct API call
- No more articles sitting on Mac but missing from meridianreader.com"""

content = content.replace(old_vps, new_vps, 1)

# Update session 55 build history — append new items
old_session_end = """**DB counts: ~847 articles after backfill + cleanup (FT ~286, Eco 327, FA 159, Bloomberg 45, Other 46)**
AI picks total: ~114"""

new_session_end = """**DB counts: ~872 articles (FT ~262, Eco 362, FA 157, Bloomberg 45, Other 46)**
AI picks total: ~114

**FA scraper overhaul (Session 55 continued)**
- Removed most-read from regular scraper — now exclusively AI pick territory
- Single latest issue only (was two); skips if URL unchanged via kt_meta watermark (`fa_last_issue_url`)
- AI pick: manually saved FA articles now scored but not duplicated (`_manual_saves` set)
- `Recent Books` and `/book-reviews/` blocked at both URL and title level
- Deleted 2 stale "Recent Books" stubs from Mac + VPS

**Auto VPS push after every sync**
- `_enrich_after_sync()` now calls `vps_push.py` after enrichment
- Applies to all sync triggers (launchd, UI, API) — articles appear on VPS immediately after scrape"""

content = content.replace(old_session_end, new_session_end, 1)

# Update outstanding issues
old_issues = """### 🔴 Session 56 — do first
1. **FA AI picks missing pub_date** — FA most-read scraper doesn't extract dates; articles fall back to saved_at in swim lanes
2. **Economist delivery gaps** — 3 zero-days (04-08, 04-11, 04-13); check bookmarks scraper logs + session health
3. **FT unenriched backlog** — 59 pending (includes 38 backfilled title_only articles); trigger enrichment
4. **API credit indicator** — no programmatic endpoint; consider failure-rate proxy in stats panel"""

new_issues = """### 🔴 Session 56 — do first
1. **FA AI picks missing pub_date** — FA most-read scraper doesn't extract dates; articles fall back to saved_at in swim lanes
2. **Economist delivery gaps** — 3 zero-days (04-08, 04-11, 04-13); check bookmarks scraper logs + session health
3. **FT unenriched backlog** — 59 pending (includes 38 backfilled title_only articles); trigger enrichment
4. **API credit indicator** — no programmatic endpoint; consider failure-rate proxy in stats panel
5. **wake_and_sync.sh push redundancy** — now that Flask auto-pushes after sync, the explicit vps_push.py call in wake_and_sync.sh is redundant for articles (but still needed for newsletters/images/interviews); review and simplify"""

content = content.replace(old_issues, new_issues, 1)

with open('/Users/alexdakers/meridian-server/NOTES.md', 'w') as f:
    f.write(content)
print("NOTES.md updated")
