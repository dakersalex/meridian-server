# Meridian — Technical Notes
Last updated: 20 April 2026 (Session 62 — Unfetchable blocklist, extension v1.5/1.6/1.7, Economist auto-sync verified)

## Overview
Personal news aggregator. Flask API + SQLite backend on Hetzner VPS (always-on).
Frontend at https://meridianreader.com/meridian.html

## Infrastructure
- VPS: Hetzner CPX22, 204.168.179.158, Ubuntu 24.04
- SSH: ssh root@204.168.179.158
- Flask: launchd service `com.alexdakers.meridian.flask` (auto-restarts), port 4242
- Sync scheduler: launchd `com.alexdakers.meridian.wakesync` (05:40 + 11:40 Geneva)
- GitHub: https://github.com/dakersalex/meridian-server

## File Locations (Mac)
- ~/meridian-server/server.py
- ~/meridian-server/meridian.html
- ~/meridian-server/meridian.db
- ~/meridian-server/rss_ai_pick.py — RSS-based AI pick pipeline (blocklist-aware)
- ~/meridian-server/backfill_keypoints.py — Key points backfill script
- ~/meridian-server/extension/ — Chrome extension v1.7 (auto-sync FT+Economist+FA, smart Sync Bookmarks)
- ~/meridian-server/wake_and_sync.sh — Scheduled sync (RSS picks, newsletters, VPS push)
- ~/meridian-server/vps_push.py
- ~/meridian-server/com.alexdakers.meridian.flask.plist — Flask auto-restart
- ~/meridian-server/com.alexdakers.meridian.wakesync.plist — Sync scheduler

## Architecture (Session 62 — Extension-based)

### How articles flow into Meridian

1. **Manual clip button** (extension popup) — on any article page → extracts body immediately → saves as `full_text`, fully enriched
2. **Manual "Sync Bookmarks" button** (extension popup) — only visible when ON a bookmarks page (FT saved, Economist bookmarks) → bulk-imports with smart stop condition (see Session 62 below)
3. **Extension auto-sync every 6h** — opens FT saved-articles, **Economist bookmarks (new in v1.7)**, and FA saved-articles in background tabs; extracts new article links; saves as `title_only`
4. **RSS AI picks** (twice daily via wake_and_sync.sh, 05:40 + 11:40 Geneva) — fetches 13 RSS feeds (FT/Economist/FA), Haiku scores candidates, auto-saves score ≥7-8. Filters via unfetchable_urls blocklist + Alphaville live-blocklist + pattern filters.
5. **Economist Weekly Edition scraper** — internal Flask scheduler fires Thursday 22:00 UTC → `ai_pick_economist_weekly()` → scrapes weekly edition via Playwright → Haiku scores → routes to Feed/Suggested. Last successful run: Apr 17.
6. **Extension body-fetcher** (every 6h, batch=10 as of v1.5) — opens `title_only` articles in background tabs using real Chrome session; extracts body text; triggers Haiku enrichment. When fetch fails, marks article `unfetchable` → server auto-adds URL to blocklist.

### What was removed (Session 61)
- Playwright scrapers for FT/Economist/FA — the standalone Playwright browsers were Cloudflare-flagged as bots. **NOTE**: this does NOT apply to the extension-based path, which runs inside your real logged-in Chrome session (no Cloudflare block). Only dedicated headless Playwright was abandoned.
- Legacy Playwright AI pick (replaced by RSS picks)
- 90-second Playwright wait + 5-minute AI pick wait from wake_and_sync.sh
- `enrich_from_title_only()` — no more fabricated summaries from titles alone

### Playwright code still active
- `ai_pick_economist_weekly()` + `eco_weekly_sub.py` — Thursday 22:00 UTC weekly edition scraper. Uses `eco_chrome_profile` directory.
- `enrich_title_only_articles()` fallback for some sources.

### wake_and_sync.sh does
- RSS pick (article discovery)
- Newsletter sync (iCloud IMAP)
- VPS push (articles, images, newsletters, interviews)
- Health check logging

### Chrome extension v1.7 does
- **Manual clip button** — one article at a time (any source), saves as `full_text`
- **Manual Sync Bookmarks button** (popup) — visible on FT saved-articles or Economist bookmarks pages; smart stop condition (see below)
- **Auto-sync FT + Economist + FA bookmarks** every 6h via alarm
- **Background body-fetcher** every 6h, 10 articles per batch
- **Unfetchable detection** — FT Professional / Alphaville / Bloomberg / Economist data pages marked `unfetchable`, server auto-blocklists URL
- **Auto-cookie harvesting** for FT + Economist when user visits those sites
- Note: Extension file edits require manual reload at chrome://extensions

## Unfetchable Blocklist (Session 62)

### Problem solved
FT Alphaville posts, FT Professional pages, Bloomberg articles (no extension session), Economist data pages produce `status='unfetchable'` after the body-fetcher fails. Previously: counted forever as "missing summaries", and RSS pick would happily re-suggest the same URL. Now: excluded from health counts AND prevented from being re-picked.

### Table: unfetchable_urls
```sql
CREATE TABLE unfetchable_urls (
  url TEXT PRIMARY KEY,
  source TEXT,
  reason TEXT DEFAULT '',
  added_at INTEGER NOT NULL
)
```

### Automatic population
When extension PATCHes `/api/articles/<id>` with `status: "unfetchable"`, `update_article()`:
1. Adds URL to `unfetchable_urls` (INSERT OR IGNORE)
2. Sets `auto_saved=0` on the article (removes from Feed)
3. Deletes matching entries from `suggested_articles`
4. Logs: "Unfetchable: blocklisted {url} and demoted from feed/suggested"

### RSS pick pre-filter (rss_ai_pick.py)
Before scoring candidates, RSS pick excludes:
1. **Live Alphaville blocklist** — fetches `https://www.ft.com/alphaville?format=rss`, adds URLs to `known`. Essential because FT Alphaville uses same `/content/<uuid>` URL structure as regular articles.
2. **DB blocklist** — all URLs in `unfetchable_urls` table
3. **Pattern match** via `is_pattern_unfetchable(url, source)`:
   - `/economic-and-financial-indicators/` in URL (Economist data pages)
   - `source == "Bloomberg"` or `bloomberg.com` in URL (manual-clip only)

### Health endpoint fix
`/api/health/daily` and `/api/health/enrichment` unenriched counts exclude `status='unfetchable'`:
```sql
WHERE (summary IS NULL OR summary='') AND (status IS NULL OR status != 'unfetchable')
```

## Smart Sync Bookmarks Stop Condition (Extension v1.6)

### Problem solved
The manual "Sync Bookmarks" popup button previously clicked Load More until the count of new-to-Meridian articles didn't increase. On a list ordered by save time with many historical bookmarks, this could go back years, opening hundreds of tabs.

### New logic in `scrollAndExtract()` (popup.js)
Two modes based on DB size:

**First-sync mode** (Meridian DB has <50 articles):
- Max 20 Load More clicks
- No consecutive-known early-stop (nothing to match)

**Incremental mode** (DB has ≥50 articles — the normal case):
- Stop after **3 consecutive known articles**
- Safety ceiling: 3 Load More clicks maximum

### Why this works
Both FT and Economist order their bookmark lists by **save time (most recent first)**. Verified via DOM inspection. On a save-time-ordered list, once you see known articles, everything below is also known — so 3 consecutive known = safe stop.

The `consecutive` counter **resets on any unknown article** — this handles the edge case where you bookmark one old article recently: it appears near the top (counter hits 1), next article is new (counter resets), keep going.

## Three-Level Reading Mode (Session 61)

### Brief / Analysis / Full text toggle on every article
- **Brief** — 2-3 sentence summary (always available)
- **Analysis** — summary + numbered key points + tags (requires key_points data)
- **Full text** — complete article in serif reader layout with highlighted passages (lazy-loaded from /api/articles/<id>/detail)

### Data fields
- `key_points` — JSON array of 4-6 substantive points extracted from article body
- `highlights` — JSON array of 3-5 exact quotes marking crucial passages
- Generated by Haiku during enrichment, stored in articles table
- Backfill: `backfill_keypoints.py` re-enriches existing articles (ran Session 61)

## Enrichment Pipeline

### How articles get enriched (body → summary + key points)
- `enrich_article_with_ai()` — sends body text (≥200 chars) to Haiku
- Returns: summary, key_points, highlights, tags, topic, pub_date
- Only works with REAL article body text — never generates from titles alone
- Extension body-fetcher triggers `/api/enrich/<id>` after fetching body

### Key endpoints
- `GET /api/health/enrichment` — ok/unenriched count/status breakdown (excludes unfetchable)
- `GET /api/health/daily` — daily health summary with alerts for notification banner (excludes unfetchable)
- `GET /api/articles/<id>/detail` — full body + key_points + highlights (lazy-loaded)
- `GET /api/articles/pending-body` — title_only articles for extension body-fetcher
- `POST /api/rss-pick` — RSS-based AI pick (blocklist-aware)
- `GET /api/sync/last-run` — latest article ingestion time per source
- `PATCH /api/articles/<id>` — auto-blocklists + demotes when status → unfetchable

## Flask Auto-Restart
- Plist: `com.alexdakers.meridian.flask.plist` installed in ~/Library/LaunchAgents/
- `KeepAlive: true` — launchd automatically restarts Flask if it crashes
- `RunAtLoad: true` — starts on login
- Verified: killing Flask process → respawns within seconds

### ⚠️ Flask restart gotcha
- `pkill -f 'python.*server.py'` does NOT reliably match the launchd-spawned Flask process (returns silently with no match)
- Correct method: `pgrep -f server.py` to find PID, then `kill <PID>` directly
- Launchd respawns within ~5-8 seconds
- **Shell bridge dies when Flask is killed** — must re-inject into Tab A after every restart:
  ```js
  window.shell = (cmd) => fetch('http://localhost:4242/api/dev/shell', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({cmd})}).then(r=>r.json());
  ```
- **Never ask Alex to run Terminal commands** — always handle restart via shell bridge + launchd respawn
- After Flask restart, verify new code is loaded by checking file modification time vs PID start time (`ps -o lstart= -p <PID>`)

## Extension Frequency Settings (v1.5+)
| Alarm | Interval | Batch |
|---|---|---|
| `syncSaves` (FT + Economist + FA bookmarks scrape) | 6 hours | — |
| `fetchBodies` (body-fetcher for title_only articles) | 6 hours | 10 articles |

Previously 2h/15min/5 respectively. Reduced to cut background tab noise — system opens ~6-8 tabs/day vs ~100+ before.

## Outstanding Issues / Next Sessions

### 🟡 Session 63 priorities
1. **Verify Economist auto-sync holds up** — after 24-48h, check logs for clean 6h cycles on `Meridian auto-sync: The Economist — N new of M total` with no Cloudflare errors
2. **Verify Alphaville blocklist works in practice** — after tomorrow's 05:40/11:40 RSS runs, check logs for "blocklisted N Alphaville URLs" + confirm no Alphaville URLs made it into feed/suggested
3. **Evaluate legacy Playwright code** — FTScraper, EconomistScraper (non-weekly), ForeignAffairsScraper classes can be removed. KEEP: `ai_pick_economist_weekly`, `eco_weekly_sub.py`, `enrich_title_only_articles` Playwright fallback paths.
4. **Clean up dead Playwright profile directories** — `ft_profile`, `fa_profile`, `bloomberg_profile`, `eco_feed_profile`, `eco_playwright_profile` are unused dead weight (~1.5 GB combined). KEEP `eco_chrome_profile` (used by weekly scraper).
5. **Key points backfill completion** — verify all 909 articles have key_points populated
6. **VPS DB sync** — push backfilled key_points/highlights to VPS + push new unfetchable_urls table schema
7. **Test Mac restart** — verify Flask auto-restart + extension resume after full reboot (will likely happen with Tahoe 26.4.1 install anyway)

### 🟢 Nice to have
- Daily email alert via iCloud SMTP when health check fails
- Economist chart backfill (173 articles)
- KT theme evolution improvements
- Mirror unfetchable_urls table to VPS for consistency
- Schedule-based syncSaves (e.g. 06:00, 12:00) instead of rolling 6h — would match wake_and_sync rhythm but requires cron-like logic in Chrome alarms (doable but fragile if Chrome closed at fire time)

## Build History

### 20 April 2026 (Session 62)

**Unfetchable article handling overhaul**
- Added `unfetchable_urls` blocklist table (url PK, source, reason, added_at)
- Seeded with 9 existing unfetchable URLs (7 FT, 1 Bloomberg, 1 Economist)
- `update_article` PATCH handler now auto-blocklists + demotes when status → unfetchable:
  - Adds URL to `unfetchable_urls`
  - Sets `auto_saved=0` (removes from Feed)
  - Deletes from `suggested_articles`
- 6 articles that were wrongly in Feed with `auto_saved=1` were demoted during seeding

**RSS pick pre-filter (rss_ai_pick.py)**
- New `fetch_unfetchable_blocklist()` — live-fetches Alphaville RSS + reads DB blocklist
- New `is_pattern_unfetchable(url, source)` — blocks Economist `/economic-and-financial-indicators/` + all Bloomberg URLs
- Applied in candidate loop before scoring — no wasted Haiku tokens on unfetchable URLs

**Health endpoint fix**
- `/api/health/daily` and `/api/health/enrichment` unenriched count now excludes `status='unfetchable'`
- Alert "N articles missing summaries" was stuck at 10 for sticky unfetchable articles; now correctly drops to reflect only genuinely-pending articles
- Post-patch: `unenriched: 4` (down from 13), `ok: true`, `alerts: []`

**Extension v1.5 — frequency reductions**
- `syncSaves` alarm: 2h → 6h (reduces bookmark-page tab openings 3×)
- `fetchBodies` alarm: 15min → 6h (reduces body-fetch tab openings 24×)
- Body-fetch batch size: 5 → 10 (maintains throughput with longer interval)
- Net effect: background tab activity dropped from ~100+ openings/day to ~6-8/day

**Extension v1.6 — smart Sync Bookmarks stop condition**
- Added first-sync mode (DB <50 articles): 20 Load More clicks max, no early stop
- Added incremental mode (DB ≥50 articles): stop after 3 consecutive known articles, 3 clicks max
- `consecutive` counter resets on any unknown article — handles "bookmarked old article recently" edge case
- Removed buggy `'more'` from Load More button text match (would've matched random "Read more" links)
- Added debug logging showing stop reason, click count, extracted article count

**Extension v1.7 — Economist added to auto-sync**
- Added Economist bookmarks (`economist.com/for-you/bookmarks`) to `SYNC_PAGES` array in background.js
- Uses `h3 a, h2 a` selector with date-pattern filter (`/20\d{2}/\d{2}/\d{2}/`) matching Economist URL structure
- SKIP list filters out nav sections (/for-you, /topics/, /tags/, etc.)
- **Verified working**: manually triggered `autoSyncSaves()` in service worker console → 6 new Economist articles added (374 → 380). All 6 matched URLs from user's actual Economist bookmarks page. Cloudflare did NOT block the extension-based approach (uses real logged-in Chrome session, not headless Playwright).

**1 orphaned FT article enriched**
- `efd80c471d240d40` — "Impact of Iran war will hurt US even after conflict ends" — had 8601-char body but no summary. Triggered `/api/enrich/` → 269-char summary generated.

**Corrections to prior NOTES.md**
- Economist scraping abandoned due to Cloudflare — applied ONLY to headless Playwright approach. Extension-based scraping works fine via real Chrome session. Added Economist to auto-sync as a result.
- "Legacy Playwright AI pick code — no longer called" — this was incorrect. `ai_pick_economist_weekly()` is still called by internal Flask scheduler every Thursday 22:00 UTC. Should be preserved, not removed.

**Disk cleanup session (unrelated to Meridian)**
- Mac was at 97% disk full (7.6 GB free of 228 GB) — causing macOS to run purge loops that made the mouse sticky
- User deleted ~30 GB of Popcorn Time video downloads + 4 GB of podcast downloads + podcast cache
- Now 151 GB used / 49 GB free / 76% capacity — healthy
- Load averages went up during cleanup (Spotlight re-indexing) — restart recommended to relieve system

**Key learnings**
- `pkill -f 'python.*server.py'` does NOT match launchd-spawned Flask — use direct `kill <PID>`
- Flask restart kills the shell bridge — must re-inject after every restart
- FT and Economist bookmark lists are both ordered by save time (most recent first), NOT publication date
- FT bookmarks page = 50 articles per page, URL-paginated (Prev/Next), no Load More
- Economist bookmarks page = 10 articles initial load, Load More button for more
- FT Alphaville URLs are indistinguishable from regular FT by URL pattern alone; only reliable detection is cross-referencing FT's own Alphaville RSS feed
- Never ask Alex to run Terminal — all operations go via shell bridge + launchd respawn
- Extension-based scraping is NOT subject to Cloudflare bot detection (uses real Chrome session); only Playwright was blocked
- Chrome MCP safety layer blocks navigation AND JS execution on economist.com — not just navigation

---

### 19 April 2026 (Session 61)

**Extension-based architecture — replaced Playwright entirely**
- Chrome extension auto-sync: FT + FA bookmarks every 2h via background tabs
- Extension body-fetcher: processes title_only articles every 15min using real browser session
- Unfetchable status: FT Professional articles detected and marked, stops retry loop
- Removed Playwright scrapers + legacy AI pick from wake_and_sync.sh (8+ min → 30 sec)

**Three-level reading mode**
- Brief / Analysis / Full text toggle on article detail view
- Key points and highlights extracted by Haiku during enrichment
- Full text lazy-loaded from /api/articles/<id>/detail endpoint
- Backfill script running for 909 existing articles

**Infrastructure improvements**
- Flask auto-restart via launchd KeepAlive plist — survives crashes
- /api/health/daily endpoint with notification banner
- Last-scraped timestamps now based on actual article saved_at, not Playwright sync
- Swim lane date fix (ISO timestamps → YYYY-MM-DD matching)
- Newsletter cards match Feed card style
- Normalized 19 pub_dates from ISO timestamps

**Bugs fixed**
- Duplicate get_article_detail endpoint causing Flask crash
- Extension SyntaxError (duplicate 'url' variable)
- FT Professional host_permissions added to manifest
- Fake title-only summaries reverted (42 Mac, 32 VPS)

**Key learnings**
- Extension file edits require Chrome reload — can't be automated, must batch changes
- Flask without auto-restart is fragile — any crash takes system down
- CORS issues when page origin (8080) differs from API (4242) after Flask restart
- Playwright scrapers were the weak link — real browser via extension is the reliable path

---

### 18 April 2026 (Session 60)
- RSS-based AI pick pipeline (rss_ai_pick.py)
- Enrichment health monitoring (/api/health/enrichment)
- FA author-URL bug fixed (38 articles)
- Batch enrichment results applied (42 articles from Session 59)

### 18 April 2026 (Session 59)
- Batch API enrichment proof of concept (50% cost savings)
- Performance fix: 4x speed from fixing SERVER variable

---

## Session startup — CRITICAL ORDER
1. `tabs_context_mcp` with `createIfEmpty:true`
2. Read NOTES.md
3. Navigate Tab A to localhost:8080 (if not already open)
4. Inject shell bridge
5. Health check via `/api/health/daily`

## Rules
- Never edit Chrome extension files without warning Alex it needs a reload — batch extension changes
- Never use `enrich_from_title_only` or generate summaries without real article body text
- Always verify `grep -c "<html lang" meridian.html` returns 1 before deploying
- Always `ast.parse()` server.py before writing
- Flask auto-restarts via launchd — kill by PID (`pgrep -f server.py` → `kill <PID>`), NOT `pkill -f`
- Re-inject shell bridge into Tab A after every Flask restart
- **Never ask Alex to run Terminal commands** — all shell operations go through the shell bridge
- Chrome MCP is blocked from navigating to / executing JS on economist.com; use DevTools + `copy()` on the user side for Economist inspection
