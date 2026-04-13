# Meridian — Technical Notes
Last updated: 13 April 2026 (Session 51 — AI pick redesign, scheduler cleanup)

## Overview
Personal news aggregator. Flask API + SQLite backend on Hetzner VPS (always-on).
Frontend at https://meridianreader.com/meridian.html

## Infrastructure
- VPS: Hetzner CPX22, 204.168.179.158, Ubuntu 24.04
- SSH: ssh root@204.168.179.158
- Flask: systemd service `meridian`, port 4242
- GitHub: https://github.com/dakersalex/meridian-server

## File Locations (Mac)
- ~/meridian-server/server.py
- ~/meridian-server/meridian.html
- ~/meridian-server/meridian.db
- ~/meridian-server/eco_scraper_sub.py   — Economist bookmarks scraper
- ~/meridian-server/eco_fetch_sub.py     — Economist article text fetcher
- ~/meridian-server/eco_backfill_dates.py — one-off pub_date backfill (keep for reference)
- ~/meridian-server/eco_chrome_profile/  — CDP Chrome profile (gitignored)
- ~/meridian-server/eco_login_setup.py   — session renewal (gitignored)
- ~/meridian-server/wake_and_sync.sh     — Mac sync + VPS push
- ~/meridian-server/logs/

## Mac Flask
- Restart: `lsof -ti tcp:4242 | xargs kill -9`
- CRITICAL: restart after every deploy

## Deploying
  cd ~/meridian-server && ./deploy.sh "message"

---

## Database (13 April 2026 — end of session 51)
| Source | Mac | VPS |
|---|---|---|
| FT | ~229 | ~229 |
| Economist | ~327 | ~327 |
| FA | ~139 | ~139 |
| Bloomberg | ~38 | ~38 |
| Other | ~18 | ~18 |
| **Total** | **~752** | **~752** |

API balance: ~$9 — ~28 days runway at ~$0.32/day

---

## Economist Scraper Architecture — CRITICAL NOTES

### NEVER use URL for Economist pub_date
The Economist URL format is `/section/YYYY/MM/DD/slug` where the date is the
**edition date**, not the individual article date. The bookmarks page shows the
correct article date as text (e.g. "Apr 9th 2026"). Always use that.

**eco_scraper_sub.py**: extracts pub_date from grandparent element text adjacent
to each article link on the bookmarks page. Pattern: `Apr 9th 2026` → `2026-04-09`.

**eco_fetch_sub.py**: extracts pub_date from `<time datetime="...">` element on
the article page, falling back to JSON-LD `datePublished`. Never uses URL.

**server.py enrichment**: already has guard `if not art.get("pub_date")` — this
is now correct since both subprocess scripts always populate pub_date from page.

### Backfill completed
`eco_backfill_dates.py` re-scraped all 307 bookmarks from the bookmarks page and
corrected 240 out of 297 Economist articles in the DB. Pushed to VPS 19:28 CEST.

### Both subprocess scripts MUST use real Chrome (not headless)
`--headless=new` breaks Economist JS rendering — bookmarks page and article pages
return 0 content. Solution: real Chrome with off-screen window.

**eco_scraper_sub.py:**
- `--window-position=-3000,-3000 --window-size=1280,900` (off-screen)
- Clicks Load More until page stops growing (32 clicks → 303+ articles)
- `scroll_into_view_if_needed()` + `page.wait_for_timeout(4000)` per click
- NO `wait_for_function` — unreliable for off-screen windows
- NO f-strings with complex interpolation in subprocess scripts

**eco_fetch_sub.py:**
- Also off-screen real Chrome
- Timeout: 600s (30 articles × ~10s = ~300s, needs headroom)
- Extracts pub_date from `<time datetime>` on article page

### Session renewal
`python3 ~/meridian-server/eco_login_setup.py`

---

## FT Scraper
- Playwright, ft_profile/, headless=True
- Paginates through all saved pages, stops when entire page all-existing
- pub_date: extracted from article page `<time>` element ✓
- 1 pending unenriched: "North Sea rethink" — unfetchable, ignore
- TODO: verify pub_dates are correct (same URL date issue may apply)

## Foreign Affairs Scraper
- Playwright, fa_profile/, headless=True
- Sources: saved articles + 3 recent issues (Mar/Apr 2026, Jan/Feb 2026, Nov/Dec 2025)
- Shared `seen` set prevents duplicates
- FA cookie expires 2026-05-23
- 11 pending unenriched on VPS — paywall-truncated stubs, need cleanup
- TODO: clean 11 FA pending + check FA pub_dates

---

## Stats Panel
- Last Scraped: reads `last_sync_ft/economist/fa` from kt_meta via `/api/sync/last-run`
- Written by `run_sync()` on every successful completion
- Bloomberg excluded (manual-only)
- Health check: collapsed by default, "Run health check" button, manual-only (~$0.003/call)
- CRITICAL: use async IIFE for `await` calls in stats panel JS — never bare await
- FIXED (Session 50): Last Scraped now correctly shows "Today" not "Yesterday" for d=0

---

## Newsletter Sync
- newsletter_sync.py polls iCloud IMAP for Bloomberg newsletters (Points of Return etc.)
- Stores in `newsletters` table (separate from `articles` table)
- UI reads from `/newsletters` endpoint on VPS — SERVER = meridianreader.com
- wake_and_sync.sh pushes newsletters Mac→VPS after each sync
- TIMING GAP: Bloomberg delivers 06:00-06:30 Geneva, morning sync runs 05:40
  → newsletter_sync at 04:30 UTC (06:30 Geneva) in Flask scheduler
  → TODO: add standalone newsletter push after the 06:30 sync

---

## Sync Architecture

### Scraping — owned exclusively by launchd
- **05:40 Geneva** — launchd triggers wake_and_sync.sh → FT + Economist + FA scrape
- **11:40 Geneva** — launchd triggers wake_and_sync.sh → FT + Economist + FA scrape
- wake_and_sync.sh: scrape → enrich → push to VPS
- CRITICAL: Flask scheduler no longer triggers scrapers — launchd is sole authority
  This was fixed Session 51d to eliminate double Playwright sessions on same profiles
  (was causing potential bot detection risk)

### Flask scheduler — post-scrape tasks only
- **06:30 Geneva (04:30 UTC)** — newsletter sync + run_agent + auto_dismiss + kt/tag-new + enrich_image_insights
- No scrape triggers in Flask scheduler

### Profile usage windows (avoid running AI pick during these)
- ft_profile/: ~05:40–06:10, ~11:40–12:10
- eco_chrome_profile/: ~05:40–06:10, ~11:40–12:10
- fa_profile/: ~05:40–06:10, ~11:40–12:10

---

## AI Pick Architecture — BEING REDESIGNED (Session 51)

### Decision: feed-scraping + Sonnet scoring
After extensive iteration (web search tool, pure recall), agreed approach:

1. **Sources:**
   - FT: `ft.com/myft/following/197493b5-7e8e-4f13-8463-3c046200835c/time` (personalised feed, auth required)
   - Economist: `economist.com/for-you/topics` (personalised topics feed, auth required, needs Load More click)
   - Foreign Affairs: `foreignaffairs.com/most-read` (public, no auth)
2. **Method:** Playwright with existing profiles (ft_profile/, eco_chrome_profile/) — same auth sessions already in use
3. **Scoring:** Single Sonnet call — pass unsaved article titles/URLs, score 0-10 against interests, return JSON
4. **Routing:** score ≥9 → Feed (auto_saved=1), score 6-8 → Suggested
5. **Cost:** ~$0.007/run (Sonnet, ~2200 input + 500 output tokens) — negligible

### Timing (agreed Session 51)
Reading windows: 06:00-10:00, 12:00-14:00, 18:30-19:30 Geneva
Safe AI pick slots (no profile conflicts with scrapers):
- **07:30 Geneva** — after morning scrape window, catches today's first FT/Economist articles
- **12:30 Geneva** — after lunch scrape window
- **17:30 Geneva** — before evening commute

### ⚠️ NOT YET BUILT — Next session
- Need new `ai_pick_feed_scrape()` function replacing `ai_pick_web_search()`
- Need new launchd plist entries for 07:30, 12:30, 17:30
- `scrape_suggested_articles()` to be hollowed out / replaced
- Gate key: single `ai_pick_last_run` per slot (morning/lunch/evening)

### Why not web search tool
- Anthropic web search tool doesn't reliably index paywalled FT/Economist articles
- Only Bloomberg (not paywalled) returned consistently
- Pure Claude recall gave 2025 articles with hallucinated URLs
- Feed scraping gives real, personalised, authenticated, live articles

---

## API Cost Profile (~$0.32/day)
- enrich_article_with_ai → Haiku (~$0.001/article, dominant cost)
- health check → Haiku, ~$0.003/call, manual-only
- AI pick → Sonnet, ~$0.007/run × 3 runs/day = ~$0.02/day (once built)
- KT theme generation → Sonnet, infrequent

---

## Outstanding Issues / Next Sessions

### 🔴 Build next session
1. Build `ai_pick_feed_scrape()` — Playwright reads FT/Economist/FA feeds, Sonnet scores
2. Add launchd slots at 07:30, 12:30, 17:30 Geneva for AI pick
3. Remove/hollow out `scrape_suggested_articles()` and `ai_pick_web_search()`

### 🔴 Priority fixes
4. FA 11 pending — delete paywall-truncated stubs from VPS
5. FA pub_dates — check if FA also has URL vs page date discrepancy
6. FT pub_dates — check if FT also has URL vs page date discrepancy
7. FA cookie renewal — expires 2026-05-23

### 🔴 Monitor
8. Economist CDP session — will expire, run eco_login_setup.py to renew

### 🟡 Planned Features
9. Newsletter push after 06:30 sync (close the VPS timing gap)
10. Daily briefing backend — briefings table, Sonnet, morning sync
11. Daily briefing UI — Read/Scan/Listen
12. Chat Q&A — keyword retrieval, Haiku

---

## Build History

### 13 April 2026 (Session 51 — multiple sub-sessions)

**51a — AI pick patches (from Session 50 backlog)**
- score >= 8 → score >= 9 in ai_pick_web_search() and run_agent()
- Once-daily gate → twice-daily (morning/midday) with slot-keyed kt_meta keys
- Gate write fixed: hardcoded 'ai_pick_last_run' → _gate_key variable
- Scheduler re-enabled: DISABLED block → live scrape_suggested_articles() + save_suggested_snapshot()
- Prompt: "Find 4-6" → "Find 4-8", "5-6: moderate" line removed

**51b — AI pick cost reduction**
- Fixed agentic loop bug: was sending stub "Search completed." — Claude never got real data
- Search window: LAST 7 DAYS → LAST 24 HOURS
- Gate simplified to once-daily
- scrape_suggested_articles() rewritten — 300 lines → 45 lines, all dead code removed
  (Playwright scoring loop, external sources call, date-lookup loop all gone)

**51c — AI pick rewrite: pure Claude recall (then abandoned)**
- Replaced ai_pick_web_search() with no-tool Haiku recall call
- Removed: _run_agentic_search, extract_pub_date_from_url, _month_name (all dead)
- Abandoned: Haiku recalled 2025 articles with hallucinated URLs — training cutoff issue
- Decided: need real web search or feed scraping

**51b/c — Backfill attempt: Apr 8-13**
- Wrote standalone backfill script using Anthropic web search tool
- Diagnosed: web search tool works server-side (server_tool_use blocks, single end_turn)
- FT/Economist not well-indexed (paywalled) — only Bloomberg articles came back reliably
- Saved 5 real Bloomberg AI picks: 3× Apr 8, 1× Apr 10, 1× Apr 13

**51d — Remove redundant Flask scrape triggers**
- SCHEDULER_TIMES_UTC (03:50, 09:50 UTC) removed from Flask scheduler
- Background: Flask scheduler was originally built for VPS; launchd for Mac
  Now both ran on Mac → double Playwright session on same profiles (bot detection risk)
- launchd is now sole scrape authority (05:40, 11:40 Geneva)
- Flask scheduler: newsletter sync + post-scrape tasks only (06:30 Geneva)

### 13 April 2026 (Session 50)
- Investigated AI pick function end-to-end
- Agreed redesign: core 4 sources only, 9-10→Feed, 6-8→Suggested, twice daily
- Patch partially applied (SELECTIVE line only saved due to early-exit bug)
- Fixed "Last Scraped: Yesterday" bug → now shows "Today" correctly
- Added newsletter-only scheduler at 04:30 UTC (06:30 Geneva)
- Investigated newsletter timing gap — Bloomberg delivers after morning push
- Manually pushed today's Points of Return to VPS

### 12 April 2026 (Session 49)
- FT, Economist, FA scrapers completely rewritten
- Economist: subprocess architecture, off-screen Chrome, Load More fix
- CRITICAL: headless=new breaks Economist — must use off-screen real Chrome
- CRITICAL: Economist URL date is edition date, not article date — always use page date
- eco_scraper_sub: extracts date from grandparent text on bookmarks page
- eco_fetch_sub: extracts date from <time datetime> on article page
- eco_backfill_dates.py: corrected 240/297 Economist pub_dates in DB + VPS
- eco_fetch_sub timeout: 300→600s
- FA: saved articles + 3 recent issues, 64→149 articles
- Stats panel: Last Scraped uses kt_meta timestamps, health check manual-only
- Fixed await-in-non-async JS bug that crashed page entirely
- Swim lanes now accurately reflect article publication dates

---

## Autonomous Mode
Never ask Alex to run Terminal commands.

### Shell bridge
```js
window.shell = (cmd) => fetch('http://localhost:4242/api/dev/shell', {
  method:'POST', headers:{'Content-Type':'application/json'},
  body:JSON.stringify({cmd})
}).then(r=>r.json());
```

### Key patterns
- Write patch scripts via filesystem:write_file → execute via window.shell()
- Always exact text str.replace() — never line-number patches
- For large blocks use positional replacement (str.find + slice) — avoids escaping
- Write new function bodies to separate .txt files to avoid escaping in patch scripts
- Shell bridge filters "api","fetch" etc — write to tmp_*.txt, read via filesystem MCP
- NEVER use bare `await` in non-async JS context — wrap in async IIFE
- NEVER use --headless=new for Economist — use off-screen window
- NEVER use f-strings with complex interpolation in subprocess scripts
- NEVER use URL date for Economist pub_date — always use page/bookmarks date
- eco_fetch_sub timeout must be ≥ (num_articles × 12s)
- NEVER let patch scripts exit early before writing — assert all patches first, write once at end

### Session startup
1. Load MCPs: tabs_context_mcp, javascript_tool, filesystem write_file
2. Read NOTES.md
3. Tab A = localhost:8080 (shell bridge), Tab B = meridianreader.com
4. Inject shell bridge into Tab A
5. Health check
