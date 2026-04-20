# Meridian — Technical Notes
Last updated: 20 April 2026 (Session 62 — Unfetchable blocklist, RSS pick pre-filter, health count fix)

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
- ~/meridian-server/extension/ — Chrome extension v1.4 (auto-sync + body-fetch)
- ~/meridian-server/wake_and_sync.sh — Scheduled sync (RSS picks, newsletters, VPS push)
- ~/meridian-server/vps_push.py
- ~/meridian-server/com.alexdakers.meridian.flask.plist — Flask auto-restart
- ~/meridian-server/com.alexdakers.meridian.wakesync.plist — Sync scheduler

## Architecture (Session 61 — Extension-based)

### How articles flow into Meridian
1. **Your manual clips** — read article → click extension clip button → full text saved immediately
2. **Extension auto-sync** (every 2h) — opens FT saved-articles + FA saved-articles in background tabs, extracts new article links, saves as title_only
3. **RSS AI picks** (twice daily via wake_and_sync.sh) — fetches 13 RSS feeds (FT/Economist/FA), Haiku scores candidates, auto-saves score ≥7-8. Now filters via unfetchable_urls blocklist + Alphaville live-blocklist + pattern filters.
4. **Extension body-fetcher** (every 15min) — opens title_only articles in background tabs using your real Chrome session, extracts body text, triggers AI enrichment. When extension marks article `unfetchable` via PATCH /api/articles/<id>, server automatically adds URL to blocklist and demotes from feed/suggested.

### What was removed (Session 61)
- Playwright scrapers for FT/Economist/FA (unreliable, paywall/Cloudflare blocked)
- Legacy Playwright AI pick (replaced by RSS picks)
- 90-second Playwright wait + 5-minute AI pick wait from wake_and_sync.sh
- `enrich_from_title_only()` — no more fabricated summaries from titles alone

### wake_and_sync.sh now does
- RSS pick (article discovery)
- Newsletter sync (iCloud IMAP)
- VPS push (articles, images, newsletters, interviews)
- Health check logging

### Chrome extension (v1.4) does
- Manual clip button (on-demand)
- Auto-sync FT + FA bookmarks (every 2h alarm)
- Background body-fetcher (every 15min alarm, 5 articles per batch)
- Unfetchable detection (FT Professional / Alphaville pages marked, stops retry)
- Cookie harvesting for FT/Economist sessions
- **Note:** Extension file edits require manual reload at chrome://extensions

## Unfetchable Blocklist (Session 62 — NEW)

### Problem solved
- FT Alphaville posts, FT Professional pages, Bloomberg articles (no extension session), and Economist data pages produce `status='unfetchable'` after the extension body-fetcher tries and fails
- Previously: these counted forever as "missing summaries" in health alerts, and there was no protection against the RSS pick re-suggesting the same unfetchable URL
- Now: they're excluded from health counts AND prevented from being re-picked

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
When extension PATCHes `/api/articles/<id>` with `status: "unfetchable"`, `update_article()` now:
1. Adds URL to `unfetchable_urls` (INSERT OR IGNORE)
2. Sets `auto_saved=0` on the article (removes from Feed)
3. Deletes matching entries from `suggested_articles`
4. Logs: "Unfetchable: blocklisted {url} and demoted from feed/suggested"

### RSS pick pre-filter (rss_ai_pick.py)
Before scoring candidates, RSS pick now excludes:
1. **Live Alphaville blocklist** — fetches `https://www.ft.com/alphaville?format=rss` and adds every URL to `known` (since FT Alphaville posts use same `/content/<uuid>` shape as regular articles, this is the only reliable detection)
2. **DB blocklist** — all URLs in `unfetchable_urls` table
3. **Pattern match** via `is_pattern_unfetchable(url, source)`:
   - `/economic-and-financial-indicators/` in URL (Economist data pages)
   - `source == "Bloomberg"` or `bloomberg.com` in URL (manual-clip only)

### Health endpoint fix
`/api/health/daily` and `/api/health/enrichment` unenriched counts now exclude `status='unfetchable'`:
```sql
WHERE (summary IS NULL OR summary='') AND (status IS NULL OR status != 'unfetchable')
```

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
- `PATCH /api/articles/<id>` — now auto-blocklists + demotes when status set to `unfetchable`

## Flask Auto-Restart (Session 61)
- Plist: `com.alexdakers.meridian.flask.plist` installed in ~/Library/LaunchAgents/
- `KeepAlive: true` — launchd automatically restarts Flask if it crashes
- `RunAtLoad: true` — starts on login
- Verified: killing Flask process → respawns within seconds

### ⚠️ Flask restart gotcha (Session 62 — NEW)
- `pkill -f 'python.*server.py'` does NOT reliably match the launchd-spawned Flask process (returns silently with no match)
- Correct method: `pgrep -f server.py` to find PID, then `kill <PID>` directly
- Launchd respawns within ~5-8 seconds
- **Shell bridge dies when Flask is killed** — must re-inject into Tab A after every restart:
  ```js
  window.shell = (cmd) => fetch('http://localhost:4242/api/dev/shell', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({cmd})}).then(r=>r.json());
  ```
- **Never ask Alex to run Terminal commands** — always handle restart via shell bridge + launchd respawn

## Outstanding Issues / Next Sessions

### 🟡 Session 63
1. **Verify Alphaville blocklist works in practice** — after tomorrow's 05:40/11:40 RSS runs, check logs for "blocklisted N Alphaville URLs" + confirm no Alphaville URLs made it into feed/suggested
2. **Evaluate legacy Playwright AI pick code** — still in server.py but no longer called. Consider removing scraper classes entirely.
3. **Economist domain blocked by Chrome MCP** — can't navigate to economist.com during sessions. Extension handles it independently but can't debug.
4. **Key points backfill completion** — verify all 909 articles have key_points populated
5. **VPS DB sync** — push backfilled key_points/highlights to VPS + push new unfetchable_urls table schema
6. **Test Mac restart** — verify Flask auto-restart + extension resume after full reboot

### 🟢 Nice to have
- Daily email alert via iCloud SMTP when health check fails
- Economist chart backfill (173 articles)
- KT theme evolution improvements
- Remove old Playwright scraper code from server.py (dead code)
- Mirror unfetchable_urls table to VPS for consistency

## Build History

### 20 April 2026 (Session 62)

**Unfetchable article handling overhaul**
- Added `unfetchable_urls` blocklist table (url PK, source, reason, added_at)
- Seeded with 9 existing unfetchable URLs (7 FT, 1 Bloomberg, 1 Economist)
- `update_article` PATCH handler now auto-blocklists + demotes when status → unfetchable
  - Adds URL to `unfetchable_urls`
  - Sets `auto_saved=0` (removes from Feed)
  - Deletes from `suggested_articles`
- 6 articles that were wrongly in Feed with `auto_saved=1` were demoted during seeding

**RSS pick pre-filter (rss_ai_pick.py)**
- New `fetch_unfetchable_blocklist()` — live-fetches Alphaville RSS + reads DB blocklist
- New `is_pattern_unfetchable(url, source)` — blocks Economist `/economic-and-financial-indicators/` + all Bloomberg URLs
- Applied in candidate loop before scoring — no wasted Haiku tokens on unfetchable URLs

**Health endpoint fix**
- `/api/health/daily` unenriched count now excludes `status='unfetchable'`
- `/api/health/enrichment` same fix
- Alert "N articles missing summaries" was stuck at 10 for sticky unfetchable articles; now correctly drops to reflect only genuinely-pending articles
- Post-patch: `unenriched: 4` (down from 13), `ok: true`, `alerts: []`

**1 orphaned FT article enriched**
- `efd80c471d240d40` — "Impact of Iran war will hurt US even after conflict ends" — had 8601-char body but no summary. Triggered `/api/enrich/` → 269-char summary generated.

**Key learnings**
- `pkill -f 'python.*server.py'` does NOT match launchd-spawned Flask — use direct `kill <PID>`
- FT Alphaville URLs are indistinguishable from regular FT articles by URL pattern alone; only reliable detection is cross-referencing FT's own Alphaville RSS feed
- Flask restart kills the shell bridge — must re-inject after every restart
- Never ask Alex to run Terminal — all operations must go via shell bridge + launchd respawn

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
