# Meridian — Technical Notes
Last updated: 12 April 2026 (Session 49 — scraper rewrite, pub_date fixes)

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

## Database (12 April 2026 — end of session)
| Source | Mac | VPS |
|---|---|---|
| FT | ~220 | ~220 |
| Economist | ~327 | ~327 |
| FA | ~149 | ~149 |
| Bloomberg | ~39 | ~39 |
| **Total** | **~781** | **~781** |

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
- TODO next session: verify pub_dates are correct (same URL date issue may apply)

## Foreign Affairs Scraper
- Playwright, fa_profile/, headless=True
- Sources: saved articles + 3 recent issues (Mar/Apr 2026, Jan/Feb 2026, Nov/Dec 2025)
- Shared `seen` set prevents duplicates
- FA cookie expires 2026-05-23
- 11 pending unenriched on VPS — paywall-truncated stubs, need cleanup
- TODO next session: clean 11 FA pending + check FA pub_dates

---

## Stats Panel
- Last Scraped: reads `last_sync_ft/economist/fa` from kt_meta via `/api/sync/last-run`
- Written by `run_sync()` on every successful completion
- Bloomberg excluded (manual-only)
- Health check: collapsed by default, "Run health check" button, manual-only (~$0.003/call)
- CRITICAL: use async IIFE for `await` calls in stats panel JS — never bare await

---

## Sync Architecture
- wake_and_sync.sh: scrape → enrich → push to VPS
- Sync windows (Geneva): 05:40 and 11:40
- push upserts all 738 articles each time

---

## API Cost Profile (~$0.32/day)
- enrich_article_with_ai → Haiku
- health check → Haiku, ~$0.003/call, manual-only
- scrape_suggested → Haiku + web_search, morning only (gated)

---

## Outstanding Issues / Next Sessions

### 🔴 Tomorrow
1. FA 11 pending — delete paywall-truncated stubs from VPS
2. FA pub_dates — check if FA also has URL vs page date discrepancy
3. FT pub_dates — check if FT also has URL vs page date discrepancy
4. FA cookie renewal — expires 2026-05-23

### 🔴 Monitor
5. Economist CDP session — will expire, run eco_login_setup.py to renew

### 🟡 Planned Features
6. Daily briefing backend — briefings table, Sonnet, morning sync
7. Daily briefing UI — Read/Scan/Listen
8. Chat Q&A — keyword retrieval, Haiku

---

## Build History

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
- Shell bridge filters "api","fetch" etc — write to tmp_*.txt
- NEVER use bare `await` in non-async JS context — wrap in async IIFE
- NEVER use --headless=new for Economist — use off-screen window
- NEVER use f-strings with complex interpolation in subprocess scripts
- NEVER use URL date for Economist pub_date — always use page/bookmarks date
- eco_fetch_sub timeout must be ≥ (num_articles × 12s)

### Session startup
1. Load MCPs: tabs_context_mcp, javascript_tool, filesystem write_file
2. Read NOTES.md
3. Tab A = localhost:8080 (shell bridge), Tab B = meridianreader.com
4. Inject shell bridge into Tab A
5. Health check
