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
- Points of Return arrives 06:00–06:30 Geneva
- Flask scheduler syncs newsletter at 06:30 Geneva (04:30 UTC)
- TODO (Session 52): add VPS push immediately after 06:30 newsletter sync
  Currently only pushed at next full sync (11:40) — not available on mobile until then

---

## Sync Architecture

### Scraping — owned exclusively by launchd
- **05:40 Geneva** — launchd triggers wake_and_sync.sh → FT + Economist + FA scrape
- **11:40 Geneva** — launchd triggers wake_and_sync.sh → FT + Economist + FA scrape
- wake_and_sync.sh: scrape → enrich → push to VPS
- CRITICAL: Flask scheduler no longer triggers scrapers — launchd is sole authority
  Fixed Session 51d — was causing double Playwright sessions on same profiles (bot risk)

### Flask scheduler — post-scrape tasks only
- **06:30 Geneva (04:30 UTC)** — newsletter sync + run_agent + auto_dismiss + kt/tag-new + enrich_image_insights
- No scrape triggers in Flask scheduler

### Profile usage windows (never run AI pick during these)
- ft_profile/: ~05:40–06:10, ~11:40–12:10
- eco_chrome_profile/: ~05:40–06:10, ~11:40–12:10
- fa_profile/: ~05:40–06:10, ~11:40–12:10

---

## AI Pick Architecture — BEING REDESIGNED (Session 51)

### Decision: feed-scraping + Sonnet scoring
After extensive iteration (web search tool, pure recall), agreed approach:

1. **Sources:**
   - FT: `ft.com/myft/following/197493b5-7e8e-4f13-8463-3c046200835c/time` (personalised feed, auth required)
   - Economist: `economist.com/for-you/topics` (personalised topics, auth required, needs Load More click)
   - Foreign Affairs: `foreignaffairs.com/most-read` (public, plain HTTP fetch)
2. **Method:** Playwright with existing profiles (ft_profile/, eco_chrome_profile/) for FT/Economist. FA is plain HTTP.
3. **Scoring:** Single Sonnet call — pass unsaved article titles/URLs, score 0-10 against interests, return JSON
4. **Routing:** score ≥9 → Feed (auto_saved=1), score 6-8 → Suggested
5. **Cost:** ~$0.007/run × 2 runs/day = ~$0.014/day — negligible

### Rationale for feed-scraping vs alternatives
- Web search tool: doesn't reliably index paywalled FT/Economist articles
- Pure Claude recall: returns 2025 articles with hallucinated URLs (training cutoff)
- Feed scraping: real URLs, real recency, personalised, no indexing gaps, no hallucination

### User reading patterns
- Reading windows: 06:00–10:00, 12:00–14:00, 18:30–19:30 Geneva
- Saved articles = primary reading queue (bookmarked on source, read later in Meridian)
- AI picks = second layer catching important articles not personally bookmarked
- Significant newsflow — not everything read each session, articles accumulate
- Timeliness not critical — just needs to be ready before next reading session

### Agreed schedule (twice daily, matching existing scrape slots)
AI pick runs inside wake_and_sync.sh after a sleep to let scrape profiles clear.

| Time (Geneva) | What runs |
|---|---|
| 05:40 | Saved article scrape (launchd → wake_and_sync.sh) |
| ~06:15 | AI pick (wake_and_sync.sh, after `sleep 300` post-scrape) |
| 06:30 | Newsletter sync + VPS push (Flask scheduler) |
| 11:40 | Saved article scrape (launchd → wake_and_sync.sh) |
| ~12:15 | AI pick (wake_and_sync.sh, after `sleep 300` post-scrape) |

No evening scrape — twice daily is sufficient given articles accumulate across sessions.
Evening commute (18:30–19:30) reads from midday AI pick + accumulated saves.

### ⚠️ NOT YET BUILT — Session 52
1. New `ai_pick_feed_scrape()` function replacing `ai_pick_web_search()`:
   - Playwright reads FT personalised feed + Economist for-you/topics (with Load More)
   - HTTP fetch for FA most-read (no auth needed)
   - Filter out URLs already in articles or suggested_articles tables
   - Single Sonnet call: score remaining candidates 0-10 against user interests
   - Save ≥9 to Feed (auto_saved=1), 6-8 to Suggested
2. Add AI pick step to wake_and_sync.sh (sleep 300 after scrape, then call AI pick endpoint)
3. Add newsletter VPS push to Flask scheduler 06:30 task
4. Remove dead stubs: `ai_pick_web_search()`, `scrape_suggested_articles()`

---

## API Cost Profile (~$0.32/day)
- enrich_article_with_ai → Haiku (~$0.001/article, dominant cost)
- health check → Haiku, ~$0.003/call, manual-only
- AI pick → Sonnet, ~$0.007/run × 2/day = ~$0.014/day (once built)
- KT theme generation → Sonnet, infrequent

---

## Outstanding Issues / Next Sessions

### 🔴 Session 52 — build first
1. `ai_pick_feed_scrape()` — Playwright FT/Economist feeds + FA most-read + Sonnet scoring
2. Add AI pick to wake_and_sync.sh (sleep 300 then call endpoint)
3. Newsletter VPS push at 06:30 Geneva

### 🔴 Priority fixes
4. FA 11 pending — delete paywall-truncated stubs from VPS
5. FA pub_dates — check if FA also has URL vs page date discrepancy
6. FT pub_dates — check if FT also has URL vs page date discrepancy
7. FA cookie renewal — expires 2026-05-23

### 🔴 Monitor
8. Economist CDP session — will expire, run eco_login_setup.py to renew

### 🟡 Planned Features
9. Daily briefing backend — briefings table, Sonnet, morning sync
10. Daily briefing UI — Read/Scan/Listen
11. Chat Q&A — keyword retrieval, Haiku

---

## Build History

### 13 April 2026 (Session 51 — multiple sub-sessions)

**51a — AI pick patches (from Session 50 backlog)**
- score >= 8 → score >= 9 in ai_pick_web_search() and run_agent()
- Once-daily gate → twice-daily with slot-keyed kt_meta keys
- Gate write fixed: hardcoded 'ai_pick_last_run' → _gate_key variable
- Scheduler re-enabled: DISABLED block → live calls
- Prompt: "Find 4-6" → "Find 4-8", "5-6: moderate" line removed

**51b — AI pick cost reduction**
- Fixed agentic loop bug: stub "Search completed." → real tool results
- Search window: LAST 7 DAYS → LAST 24 HOURS
- Gate simplified to once-daily
- scrape_suggested_articles() rewritten — 300 lines → 45 lines, all dead code removed

**51c — AI pick rewrite attempts**
- Pure Claude recall: abandoned — Haiku recalled 2025 articles, hallucinated URLs
- Web search tool backfill (Apr 8-13): FT/Economist not indexed, Bloomberg only
- Final decision: feed-scraping approach (Playwright + Sonnet)
- Removed: _run_agentic_search, extract_pub_date_from_url, _month_name

**51d — Remove redundant Flask scrape triggers**
- SCHEDULER_TIMES_UTC (03:50, 09:50 UTC) removed from Flask scheduler
- Was causing double Playwright sessions on same profiles (bot detection risk)
- launchd is now sole scrape authority

### 13 April 2026 (Session 50)
- Investigated AI pick function end-to-end
- Agreed redesign: core 4 sources only, 9-10→Feed, 6-8→Suggested, twice daily
- Fixed "Last Scraped: Yesterday" bug
- Added newsletter-only scheduler at 04:30 UTC (06:30 Geneva)

### 12 April 2026 (Session 49)
- FT, Economist, FA scrapers completely rewritten
- Economist: subprocess architecture, off-screen Chrome, Load More fix
- CRITICAL: headless=new breaks Economist — must use off-screen real Chrome
- CRITICAL: Economist URL date is edition date — always use page date
- eco_backfill_dates.py: corrected 240/297 Economist pub_dates
- FA: saved articles + 3 recent issues, 64→149 articles
- Fixed await-in-non-async JS bug

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
- For large blocks use positional replacement (str.find + slice)
- Write new function bodies to separate .txt files to avoid escaping in patch scripts
- Shell bridge filters "api","fetch" etc — write to tmp_*.txt, read via filesystem MCP
- NEVER use bare `await` in non-async JS context — wrap in async IIFE
- NEVER use --headless=new for Economist — use off-screen window
- NEVER use f-strings with complex interpolation in subprocess scripts
- NEVER use URL date for Economist pub_date — always use page/bookmarks date
- eco_fetch_sub timeout must be ≥ (num_articles × 12s)
- NEVER let patch scripts exit early before writing — assert all patches first, write once

### Session startup
1. Load MCPs: tabs_context_mcp, javascript_tool, filesystem write_file
2. Read NOTES.md
3. Tab A = localhost:8080 (shell bridge), Tab B = meridianreader.com
4. Inject shell bridge into Tab A
5. Health check
