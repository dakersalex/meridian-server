# Meridian — Technical Notes
Last updated: 12 April 2026 (Session 49 — scraper rewrite, Economist Load More fix)

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

## Database (12 April 2026 — end of session)
| Source | Mac | VPS (pre-push) |
|---|---|---|
| FT | ~210 | ~217 |
| Economist | ~327 | ~297 |
| FA | ~128 | ~138 |
| Bloomberg | ~39 | ~39 |

NOTE: VPS push not yet done at session end — needs push next session
NOTE: 30 Economist title_only articles — enrichment running at session end

API balance: ~$9 — ~28 days runway

---

## Economist Scraper Architecture — CRITICAL NOTES

### Both subprocess scripts MUST use real Chrome (not headless)
`--headless=new` breaks Economist JS rendering — bookmarks page and article pages
both return 0 content in headless mode. Solution: real Chrome with off-screen window.

**eco_scraper_sub.py:**
- Uses `--window-position=-3000,-3000 --window-size=1280,900` (off-screen)
- Clicks Load More until page stops growing (confirmed: 32 clicks, 303 articles)
- Uses `scroll_into_view_if_needed()` + `page.wait_for_timeout(4000)` per click
- NO `wait_for_function` — unreliable for off-screen windows
- Passes `known_ids` to avoid re-adding existing articles

**eco_fetch_sub.py:**
- Also uses off-screen real Chrome (same reason)
- Timeout: 600s (30 articles × ~10s each = ~300s, needs headroom)
- Multiple selectors: `[data-component="paragraph"]` → article body fallbacks

### Stopping logic
- Load More: stop when page count stops increasing after click (not batch-based)
- First confirmed full scrape: 32 Load More clicks, 303 articles visible

### Session renewal
`python3 ~/meridian-server/eco_login_setup.py`

---

## FT Scraper
- Playwright, ft_profile/, headless=True
- Paginates through all pages, stops when entire page all-existing
- Fetches text + enriches immediately per new article

## Foreign Affairs Scraper
- Playwright, fa_profile/, headless=True
- Sources: saved articles + 3 recent issues (Mar/Apr 2026, Jan/Feb 2026, Nov/Dec 2025)
- Shared `seen` set prevents duplicates across sources
- URL filter: exactly 2 path segments, slug ≥15 chars
- FA cookie expires 2026-05-23

---

## Stats Panel
- Last Scraped: reads `last_sync_ft/economist/fa` from kt_meta via `/api/sync/last-run`
- Written by `run_sync()` on every successful completion
- Bloomberg excluded (manual-only)
- Health check: collapsed by default, "Run health check" button, manual-only (~$0.003/call)
- CRITICAL: use async IIFE for `await` calls in stats panel JS (not bare await)

---

## Sync Architecture
- wake_and_sync.sh: scrape → enrich → push to VPS
- Sync windows (Geneva): 05:40 and 11:40
- Push query: `WHERE status IN ('full_text','fetched','title_only','agent')`

---

## Enrichment Pipeline
1. `enrich_article_with_ai()` — Haiku, summary/topic/tags
2. `enrich_title_only_articles()` — fetch text + enrich title_only/agent
3. `enrich_fetched_articles()` — enrich articles with body but no summary
4. Both 2+3 run after sync and via `/api/enrich-title-only`

---

## Outstanding Issues / Next Steps

### 🔴 Must do next session
1. VPS push — 30+ Economist articles not yet on VPS
2. Verify 30 title_only Economist articles got enriched (running at session end)
3. FA cookie renewal — expires 2026-05-23

### 🔴 Monitor
4. Economist CDP session — will expire, run eco_login_setup.py to renew

### 🟡 Planned Features
5. Daily briefing backend — briefings table, Sonnet, morning sync
6. Daily briefing UI — Read/Scan/Listen
7. Chat Q&A — keyword retrieval, Haiku

---

## Build History

### 12 April 2026 (Session 49)
- FT, Economist, FA scrapers completely rewritten
- Economist subprocess architecture: event loop fix, off-screen window
- CRITICAL: headless=new breaks Economist — must use off-screen real Chrome
- Load More: fixed stop logic (page size not batch content)
- Load More: fixed click reliability (scroll_into_view + 4s wait, no f-string)
- eco_fetch_sub timeout: 300→600s
- FA: saved articles + 3 recent issues, 64→138 articles
- Stats panel: Last Scraped uses kt_meta timestamps, health check manual-only
- Fixed await-in-non-async JS bug that crashed page entirely
- DB cleanup: 28 stale articles deleted, all sources 100% full text

### 11 April 2026 (Session 48)
Full sync fixes, Economist CDP, enrichment pipeline, push query fix.

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
- Shell bridge filters "api","fetch" etc — write to tmp_*.txt
- NEVER use bare `await` in non-async JS context — wrap in async IIFE
- NEVER use --headless=new for Economist — use off-screen window
- NEVER use f-strings with complex interpolation in subprocess scripts
- eco_fetch_sub timeout must be ≥ (num_articles × 12s)

### Session startup
1. Load MCPs: tabs_context_mcp, javascript_tool, filesystem write_file
2. Read NOTES.md
3. Tab A = localhost:8080 (shell bridge), Tab B = meridianreader.com
4. Inject shell bridge into Tab A
5. Health check
