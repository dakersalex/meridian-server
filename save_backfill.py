import re

with open('/Users/alexdakers/meridian-server/NOTES.md', 'r') as f:
    content = f.read()

# Update header
content = content.replace(
    "Last updated: 15 April 2026 (Session 55 — AI pick fixes, backfill 38 missed articles)",
    "Last updated: 15 April 2026 (Session 55 — AI pick fixes, backfill, JSON scoring overhaul)"
)

# Update session 55 build history entry
old_session = """**AI pick fixes (all deployed)**
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

**DB counts: ~863 articles (286 FT, 327 Eco, 159 FA, 45 Bloomberg, 46 other)**"""

new_session = """**AI pick fixes (all deployed)**
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

**JSON scoring overhaul — flat integer array**
- Root cause of 11:47 score parse failure: Sonnet included quoted strings in reason text
  containing apostrophes/quotes which broke JSON parsing → entire batch discarded
- Fix: changed scoring prompt to return flat integer array `[7, 4, 9, 6, 8]` — no strings, unbreakable
- Fallback: if JSON parse fails, extract integers directly from raw text via regex
- Routing updated: `_scores[i]` is now an int directly, not a dict
- Reason text removed from scoring — not displayed anywhere in UI anyway

**Backfill**
- Ran `backfill_ai_picks.py` against last 14 days of FT feed
- 126 candidates scored in 3 batches of 50
- 38 saved to Feed (score >=8), 54 to Suggested (score 6-7)
- Notable picks: Iran war/ceasefire, Fed energy debate, Wall Street trading boom,
  Anthropic cyber risk, Gates of Hormuz, dollar weakness, China export controls
- Backfill URL bug: script prepended `https://www.ft.com` to already-full URLs
  → 38 malformed articles with doubled domain created then deleted from Mac + VPS
- Backfill script fixed: URL construction now checks if URL already starts with `http`

**Swim lane / AI picks clarification**
- Swim lane groups by pub_date not saved_at
- "4 picks today" is correct — those 4 have pub_date=2026-04-15
- Other 42 backfilled picks show in correct historical swim lanes (Apr 8-14)

**Model retirement fix**
- All 7 instances of `claude-sonnet-4-20250514` in meridian.html updated to `claude-sonnet-4-6`
- Retirement date: June 15 2026

**`/api/dev/restart` endpoint**
- New endpoint: spawns new Flask process in detached thread, exits cleanly
- Shell bridge gets response before old process dies → no launchd throttle loop

**DB counts: ~847 articles after backfill + cleanup (FT ~286, Eco 327, FA 159, Bloomberg 45, Other 46)**
AI picks total: ~114"""

content = content.replace(old_session, new_session, 1)

# Update outstanding issues — add JSON scoring note, remove model retirement
old_issues = """### 🔴 Session 56 — do first
1. **FA AI picks missing pub_date** — add pub_date to Sonnet scoring prompt response for FA articles
2. **Economist delivery gaps** — 3 zero-days (04-08, 04-11, 04-13); check bookmarks scraper logs + session health
3. **FT 13 unenriched articles** — check enrichment pipeline, may need manual trigger
4. **API credit indicator** — no programmatic endpoint; consider failure-rate proxy in stats panel"""

new_issues = """### 🔴 Session 56 — do first
1. **FA AI picks missing pub_date** — FA most-read scraper doesn't extract dates; articles fall back to saved_at in swim lanes
2. **Economist delivery gaps** — 3 zero-days (04-08, 04-11, 04-13); check bookmarks scraper logs + session health
3. **FT unenriched backlog** — 59 pending (includes 38 backfilled title_only articles); trigger enrichment
4. **API credit indicator** — no programmatic endpoint; consider failure-rate proxy in stats panel"""

content = content.replace(old_issues, new_issues, 1)

with open('/Users/alexdakers/meridian-server/NOTES.md', 'w') as f:
    f.write(content)
print("NOTES.md updated")
