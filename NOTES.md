# Meridian — Technical Notes
Last updated: 16 April 2026 (Session 56 start — NOTES cleanup, MCP startup fix)

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
- ~/meridian-server/eco_login_setup.py   — Economist session renewal (gitignored)
- ~/meridian-server/eco_playwright_browse.py — opens eco_playwright_profile for browsing
- ~/meridian-server/wake_and_sync.sh     — Mac sync + VPS push + AI pick trigger
- ~/meridian-server/vps_push.py          — incremental VPS article push + kt_meta sync
- ~/meridian-server/logs/

## Mac Flask
- **Clean restart (preferred):** `POST /api/dev/restart` — Flask spawns new process and exits cleanly, shell bridge survives
  ```js
  fetch('http://localhost:4242/api/dev/restart', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'})
  ```
- **Fallback if Flask is down:** `nohup bash -c "sleep 0.5 && lsof -ti tcp:4242 | xargs kill -9 2>/dev/null && sleep 2 && python3 ~/meridian-server/server.py" > /dev/null 2>&1 &`
  Fire-and-forget (no await) so shell bridge survives long enough
- **Last resort:** `python3 ~/meridian-server/server.py &` directly in Terminal
- CRITICAL: restart after every deploy
- launchd throttles after repeated kills in quick succession — use /api/dev/restart to avoid this

## Deploying
  cd ~/meridian-server && ./deploy.sh "message"

---

## Database (15 April 2026 — end of session 55)
| Source | Mac | VPS |
|---|---|---|
| FT | ~286 | ~286 |
| Economist | ~327 | ~327 |
| FA | ~159 | ~159 |
| Bloomberg | ~45 | ~45 |
| Other | ~46 | ~46 |
| **Total** | **~863** | **~863** |

AI picks in Feed (auto_saved=1): ~106 (38 backfilled this session)
API balance: check console.anthropic.com

---

## VPS Push Architecture (rebuilt Session 54)

### New behaviour
- `vps_push.py` — standalone script, called from wake_and_sync.sh AND automatically after every `/api/sync`
- Reads `last_push_ts` watermark from kt_meta → only pushes articles newer than that
- Always pushes last 48h to catch enrichment updates on recently saved articles
- After article push, explicitly pushes `last_sync_ft/economist/fa` to VPS via `/api/push-meta`
- Normal syncs: ~5-20 articles pushed instead of 771
- New `/api/push-meta` endpoint on server.py (both Mac + VPS) — upserts kt_meta key-value pairs

### Auto-push after every sync (Session 55)
- `_enrich_after_sync()` in Flask now calls `vps_push.py` as subprocess after enrichment completes
- Applies to ALL sync triggers: launchd schedule, UI "Sync all" button, direct API call
- No more articles sitting on Mac but missing from meridianreader.com

---

## Economist Scraper Architecture — CRITICAL NOTES

### NEVER use URL for Economist pub_date
The Economist URL format is `/section/YYYY/MM/DD/slug` where the date is the
**edition date**, not the individual article date. Always use page/bookmarks date.

### Both subprocess scripts MUST use real Chrome (not headless)
`--headless=new` breaks Economist JS rendering. Solution: real Chrome off-screen.

**eco_scraper_sub.py:** `--window-position=-3000,-3000 --window-size=1280,900` (off-screen)
**eco_fetch_sub.py:** Also off-screen real Chrome, timeout: 600s

### Session renewal
`python3 ~/meridian-server/eco_login_setup.py`
CRITICAL: Never open visible Chrome windows — always fail gracefully if session expired.

---

## FT Scraper
- Playwright, ft_profile/, headless=True
- Paginates through all saved pages
- pub_date: extracted from article page `<time>` element

## Foreign Affairs Scraper (overhauled Session 55)

### Architecture
- Playwright, fa_profile/, headless=True
- FA cookie expires 2026-05-23
- Two sources per run:
  1. **Saved articles** — `/my-foreign-affairs/saved-articles` (every run)
  2. **Latest issue only** — dynamically discovered from `/issues`; skipped if URL matches `fa_last_issue_url` in kt_meta
- Most-read **removed from scraper** — handled exclusively by AI pick pipeline
- Uses `h3 a` CSS selector
- SKIP_PREFIXES includes `/book-reviews/`; title blocklist includes "Recent Books"
- URL normalisation: strips `https://www.foreignaffairs.com` before SKIP_PREFIXES check

### Issue watermark
- `fa_last_issue_url` in kt_meta — skips issue if URL unchanged since last scrape

---

## Sync Architecture

### Scraping — owned exclusively by launchd
- **05:40 Geneva** — wake_and_sync.sh → FT + Economist + FA scrape
- **11:40 Geneva** — wake_and_sync.sh → FT + Economist + FA scrape

### wake_and_sync.sh flow
1. Trigger `/api/sync`
2. Sleep 90s → enrichment
3. Newsletter sync
4. `python3 vps_push.py`
5. Push images/newsletters/interviews → VPS
6. Sleep 300s
7. Trigger `/api/ai-pick`

---

## AI Pick Architecture (Session 55)

### Sources
1. **FT personalised feed** — `ft.com/myft/following/197493b5.../time`
   - Subprocess off-screen Chrome, `_feedTimelineTeasers` JS variable
   - pub_date: from `publishedDate` field ✅

2. **Foreign Affairs /search** — `foreignaffairs.com/search`
   - Playwright, fa_profile/, headless (added Session 55)
   - pub_date extracted from card text ("April 15, 2026" → YYYY-MM-DD) ✅
   - Standfirst extracted for better scoring accuracy ✅
   - Returns ~28 most recent FA articles per run

3. **Foreign Affairs most-read** — **PENDING REMOVAL Session 56**
   - Superseded by /search; no pub_date, title-only scoring
   - Check: `grep "FA_MOST_READ" ~/meridian-server/server.py`

4. **Economist weekly edition** (Thursday nights)
   - `economist.com/weeklyedition/YYYY-MM-DD` via CDP
   - Gate key: `ai_pick_economist_weekly_YYYY-MM-DD`

### Candidate filtering — PENDING FIX Session 56
- **Current (broken):** single 50-article cap across all sources sorted by pub_date
  - FT dominates; FA with blank pub_dates sorted to bottom
- **Pending:** per-source caps — FT=30, FA=15, Economist=20
  - Check: `grep "PER_SOURCE_CAPS" ~/meridian-server/server.py`

### Scoring
- Flat integer array `[7, 4, 9, 6, 8]` — eliminates JSON parse failures
- Fallback: extract integers via regex
- Sonnet, max_tokens=6000, timeout=120
- Gate: hour<13 morning / hour>=13 midday; threshold >=8 → Feed, 6-7 → Suggested
- Manual saves: scored but not duplicated (`_manual_saves` set)

### Schedule
| Time (Geneva) | What runs |
|---|---|
| ~06:15 | AI pick — FT feed + FA /search |
| ~12:15 | AI pick — FT feed + FA /search |
| Thu ~23:00 | Economist weekly edition pick |

---

## Outstanding Issues / Next Sessions

### 🔴 Session 56 — do first (in order)
1. **Remove FA most-read from AI pick** — superseded by /search
   Verify: `grep "FA_MOST_READ" ~/meridian-server/server.py`
2. **Per-source caps for AI pick** — FT=30, FA=15, Economist=20
   Verify: `grep "PER_SOURCE_CAPS" ~/meridian-server/server.py`
3. **Verify FA /search working** — first full run was interrupted by Flask restart; check today's 06:15 logs
4. **Economist delivery gaps** — zero-days on 04-08, 04-11, 04-13
5. **FT unenriched backlog** — 59 pending title_only articles
6. **API credit indicator** — consider failure-rate proxy in stats panel
7. **wake_and_sync.sh push redundancy** — Flask auto-pushes now; explicit vps_push.py call redundant for articles

### 🔴 Priority fixes
- Economist scraper: login-redirect detection
- FA cookie renewal — expires 2026-05-23
- eco_playwright_profile — Cloudflare-blocked

### 🟡 Planned Features
- Daily briefing backend
- Chat Q&A

---

## Build History

### 15 April 2026 (Session 55)
- AI pick fixes: max_tokens 2000→6000, timeout 60→120, 36h filter, gate hour<13, threshold >=8
- Flat integer array scoring — eliminates JSON parse failures from quoted strings
- FT backfill: 14 days, 38→Feed, 54→Suggested
- FA scraper: most-read removed, single latest issue + watermark, URL normalisation fix
- FA /search added as AI pick source (pub_dates + standfirst)
- Auto VPS push after every sync via `_enrich_after_sync()`
- Model retirement: `claude-sonnet-4-20250514` → `claude-sonnet-4-6` (7 instances in meridian.html)
- `/api/dev/restart` endpoint

### 14 April 2026 (Session 54)
- VPS push overhaul (watermark, push-meta endpoint)
- FA scraper rebuild (h3 a selector, dynamic issue discovery)
- Last Scraped display fix (SERVER prefix)

### 13 April 2026 (Sessions 52-53)
- AI pick pipeline: FT feed + FA most-read + Economist weekly
- Taste profile (44 topics + 100 save titles)
- Fixed FT AI pick pub_dates; renewed eco_chrome_profile

### 12 April 2026 (Sessions 49-51)
- FT, Economist, FA scrapers completely rewritten
- Economist: subprocess architecture, off-screen Chrome

---

## Autonomous Mode
Never ask Alex to run Terminal commands — Claude executes everything.

### Shell bridge
```js
window.shell = (cmd) => fetch('http://localhost:4242/api/dev/shell', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({cmd})}).then(r=>r.json());
```

### Key patterns
- Write patch scripts via filesystem:write_file → execute via window.shell()
- Always exact text str.replace() — never line-number patches
- Shell bridge filters "api","fetch","push" etc — write to logs/*.txt, read via filesystem MCP
- NEVER use bare `await` in non-async JS context — wrap in async IIFE
- NEVER use --headless=new for Economist — use off-screen window
- NEVER use f-strings with complex interpolation in subprocess scripts
- NEVER use URL date for Economist pub_date
- NEVER kill Chrome (pkill Google Chrome) — kills MCP extension tabs
- eco_fetch_sub timeout must be ≥ (num_articles × 12s)

### Session startup — CRITICAL ORDER
0. **Click Claude extension icon in Chrome toolbar** — wakes the service worker (Chrome suspends it after ~30s inactivity; looks connected but isn't until clicked)
1. `tabs_context_mcp` with `createIfEmpty:true` → get Tab A (localhost:8080) and Tab B (meridianreader.com) IDs
2. Read NOTES.md
3. Navigate Tab A to `http://localhost:8080/meridian.html` if not already there
4. Inject shell bridge into Tab A
5. Health check

### Why Chrome MCP appears disconnected at session start
Chrome MCP uses a Manifest V3 service worker which Chrome suspends after ~30s of inactivity.
The extension badge looks active but the worker is asleep. Clicking the extension icon wakes it.
This is a Chrome constraint — not fixable without Anthropic changing the extension architecture.
