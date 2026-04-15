# Meridian — Technical Notes
Last updated: 14 April 2026 (Session 54 — VPS push overhaul, FA scraper rebuild, Last Scraped fix)

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
- Restart (clean, avoids shell bridge dying): 
  `nohup bash -c "sleep 1 && kill $(lsof -ti tcp:4242) && sleep 2 && python3 ~/meridian-server/server.py" > /dev/null 2>&1 &`
- CRITICAL: restart after every deploy
- launchd throttles after repeated kills — if stuck, run `python3 ~/meridian-server/server.py &` directly in Terminal
- computer tool (Chrome MCP) cannot switch apps or open Terminal — must use shell bridge or Terminal manually

## Deploying
  cd ~/meridian-server && ./deploy.sh "message"

---

## Database (14 April 2026 — end of session 54)
| Source | Mac | VPS |
|---|---|---|
| FT | ~248 | ~248 |
| Economist | ~327 | ~327 |
| FA | ~144 | ~144 |
| Bloomberg | ~45 | ~45 |
| Other | ~46 | ~46 |
| **Total** | **~810** | **~810** |

AI picks in Feed (auto_saved=1): ~68
API balance: ~$9

---

## VPS Push Architecture (rebuilt Session 54)

### Old behaviour (broken)
- wake_and_sync.sh pushed ALL 771 articles every sync via inline heredoc Python
- No time filter → 16 HTTP batches per run → frequent timeouts
- kt_meta (last_sync_* timestamps) never pushed → "Last Scraped" always showed stale on VPS

### New behaviour
- `vps_push.py` — standalone script, called from wake_and_sync.sh
- Reads `last_push_ts` watermark from kt_meta → only pushes articles newer than that
- Always pushes last 48h to catch enrichment updates on recently saved articles
- After article push, explicitly pushes `last_sync_ft/economist/fa` to VPS via `/api/push-meta`
- Normal syncs: ~5-20 articles pushed instead of 771
- New `/api/push-meta` endpoint on server.py (both Mac + VPS) — upserts kt_meta key-value pairs

### Last Scraped display fix
- Bug: stats panel fetch used bare `/api/sync/last-run` (no SERVER prefix) → hit port 8080 → HTML 404
- Fix: added `SERVER+` prefix to both `/api/sync/last-run` and `/api/health-check` fetches
- Now durably correct: kt_meta push guarantees VPS timestamps update every sync

---

## Economist Scraper Architecture — CRITICAL NOTES

### NEVER use URL for Economist pub_date
The Economist URL format is `/section/YYYY/MM/DD/slug` where the date is the
**edition date**, not the individual article date. Always use page/bookmarks date.

### Both subprocess scripts MUST use real Chrome (not headless)
`--headless=new` breaks Economist JS rendering. Solution: real Chrome off-screen.

**eco_scraper_sub.py:**
- `--window-position=-3000,-3000 --window-size=1280,900` (off-screen)
- Clicks Load More until page stops growing
- NO f-strings with complex interpolation

**eco_fetch_sub.py:**
- Also off-screen real Chrome
- Timeout: 600s

### Session renewal
`python3 ~/meridian-server/eco_login_setup.py`
Session expires periodically (~months). When expired, scrapers hit login page.
CRITICAL: Never open visible Chrome windows without user knowing — always fail gracefully
if session expired (log warning, don't hang on login page).

---

## FT Scraper
- Playwright, ft_profile/, headless=True
- Paginates through all saved pages
- pub_date: extracted from article page `<time>` element

## Foreign Affairs Scraper (rebuilt Session 54)

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
- Had been silently returning 0 for weeks

### pub_date status
- 144 FA articles, 141 have correct pub_dates
- 3 blanks were AI pick articles (saved_at used as fallback in swim lanes)
- Swim lane fallback: frontend uses `saved_at` when `pub_date` missing/invalid → articles appear on scrape date not pub date

---

## Sync Architecture

### Scraping — owned exclusively by launchd
- **05:40 Geneva** — launchd triggers wake_and_sync.sh → FT + Economist + FA scrape
- **11:40 Geneva** — launchd triggers wake_and_sync.sh → FT + Economist + FA scrape
- launchd is sole scrape authority — Flask scheduler no longer triggers scrapers

### wake_and_sync.sh flow
1. Wait for Flask
2. Trigger `/api/sync` (FT + Economist bookmarks + FA)
3. Sleep 90s
4. Trigger `/api/enrich-title-only`
5. Trigger `/api/newsletters/sync`
6. **`python3 vps_push.py`** — incremental article push + kt_meta sync to VPS
7. Push images → VPS
8. Push newsletters → VPS
9. Push interviews → VPS
10. **Sleep 300s** (wait for scrape profiles to clear)
11. **Trigger `/api/ai-pick`** (FT feed + FA most-read, Sonnet scoring)

### Flask scheduler — post-scrape tasks only
- **06:30 Geneva (04:30 UTC)** — newsletter sync + newsletter VPS push + run_agent +
  auto_dismiss + kt/tag-new + enrich_image_insights
- **Thu 22:00 UTC** — Economist weekly edition AI pick

---

## AI Pick Architecture — LIVE (Session 52)

### Sources
1. **FT personalised feed** — `ft.com/myft/following/197493b5.../time`
   - Uses `ft_profile/` via subprocess off-screen Chrome
   - Extracts `_feedTimelineTeasers` JS variable — contains title, URL, publishedDate, standfirst
   - Filters: podcasts excluded, already-saved excluded
   - pub_date: from `publishedDate` field (ISO timestamp → YYYY-MM-DD) ✅ correct

2. **Foreign Affairs most-read** — `foreignaffairs.com/most-read`
   - Plain HTTP fetch, no auth needed
   - pub_date: still blank ← outstanding fix needed

3. **Economist weekly edition** (Thursday nights)
   - `economist.com/weeklyedition/YYYY-MM-DD` via CDP (eco_chrome_profile)
   - Runs Thu 22:00 UTC, once per edition
   - Gate key: `ai_pick_economist_weekly_YYYY-MM-DD`
   - pub_date: edition date string ✅ correct

### pub_date known issues
- **FA AI picks have no pub_date** — FA most-read scraper doesn't extract dates
  FIX PENDING: add pub_date to Sonnet scoring prompt response for FA articles

### Economist feed pages — NOT scraped (Cloudflare blocks all approaches)
- WORKAROUND: `eco_playwright_profile/` being built up via `eco_playwright_browse.py`
  Run occasionally to build browsing history
- For now: Economist covered weekly via edition page (CDP works fine there)

### Scoring
- Single Sonnet call per run
- Uses: followed topics (44) + last 100 save titles (taste profile)
- Gate: twice daily (morning/midday) for FT/FA, once weekly for Economist

### Taste profile (kt_meta keys)
- `ai_pick_followed_topics` — 44 topics from FT + Economist topic pages
  FT: AI, Citigroup, Emerging markets, Equities, Eurozone economy, Global growth,
  Global trade, Hedge funds, Luxury goods, Private equity, US economy,
  War in Ukraine, Wealth management
  Economist: Donald Trump, Xi Jinping, Keir Starmer, Stocks, Finance & Economics,
  Finance, Economics, Defence, Ukraine at war, Geopolitics, War in Middle East,
  China's economy, Investing, AI, Economy
  Core: Iran, Iran war, Strait of Hormuz, Tariffs, Trade war, Sanctions,
  Central banking, Fed, Interest rates, China, US-China, NATO, Russia, Energy, Oil
- `ai_pick_taste_titles` — last 100 manually saved article titles, auto-updated on Feed save

### Scoring bands
- 9-10: Concrete breaking event (war, sanctions, central bank decision, market shock)
- 7-8: High-quality analysis (markets, geopolitics, AI with real-world impact)
- 6: Relevant essays/analysis on followed topics
- 0-5: Not relevant

### Schedule
| Time (Geneva) | What runs |
|---|---|
| 05:40 | Saved article scrape (launchd) |
| ~06:15 | AI pick — FT feed + FA most-read (wake_and_sync.sh, after sleep 300) |
| 06:30 | Newsletter sync + VPS push |
| 11:40 | Saved article scrape (launchd) |
| ~12:15 | AI pick — FT feed + FA most-read |
| Thu ~23:00 | Economist weekly edition pick |

### Cost
- Sonnet: ~$0.015/run × 2/day + ~$0.02/week = ~$0.05/day
- Total with enrichment: ~$0.35/day

---

## Newsletter Sync
- Points of Return arrives 06:00–06:30 Geneva
- Flask scheduler: newsletter sync at 06:30 + immediate VPS push
- wake_and_sync.sh also pushes newsletters on each full sync

---

## API Cost Profile (~$0.35/day)
- enrich_article_with_ai → Haiku (~$0.001/article)
- AI pick → Sonnet, ~$0.05/day
- health check → Haiku, ~$0.003/call, manual-only
- KT theme generation → Sonnet, infrequent

---

## Outstanding Issues / Next Sessions

### 🔴 Session 55 — do first
1. **FA AI picks missing pub_date** — add pub_date to Sonnet scoring prompt response for FA articles
2. **Economist delivery gaps** — 3 zero-days (04-08, 04-11, 04-13); check bookmarks scraper logs + session health
3. **FT 13 unenriched articles** — check enrichment pipeline, may need manual trigger

### 🔴 Priority fixes
4. Economist scraper: add login-redirect detection — fail gracefully, don't hang
5. FA cookie renewal — expires 2026-05-23
6. eco_playwright_profile — continue building browsing history for Economist feed access

### 🟡 Planned Features
7. Daily briefing backend
8. Chat Q&A

---

## Build History

### 14 April 2026 (Session 54)

**Core achievements:** VPS push overhaul, FA scraper rebuild, Last Scraped display fix

**VPS push overhaul**
- Old: pushed all 771 articles every sync (no time filter) → frequent timeouts → stale VPS timestamps
- New: `vps_push.py` with `last_push_ts` watermark — only pushes articles newer than last push (min 48h)
- New: `/api/push-meta` endpoint — explicitly syncs `last_sync_*` kt_meta keys to VPS every run
- Result: ~5-20 articles per sync instead of 771; Last Scraped reliably shows "Today"

**Last Scraped display fix**
- Root cause: stats panel fetch used bare `/api/sync/last-run` without `SERVER` prefix → hit port 8080 → HTML 404 → silent catch → fallback to hardcoded `99`
- Same bug on `/api/health-check` fetch
- Fix: added `SERVER+` prefix to both fetches in meridian.html

**FA scraper rebuild**
- Root cause of 0 new articles: 3 hardcoded issue URLs, all already fully scraped
- Rebuilt `ForeignAffairsScraper` with: `h3 a` selector, dynamic issue discovery from `/issues`, most-read as third source
- Added `/book-reviews/` to SKIP_PREFIXES; deleted 2 "Recent Books" stubs from Mac + VPS
- Fixed blank pub_date on "How Long Can the Iranian Regime Hold On?" → 2026-03-03
- First run with new scraper: 7 new articles (1 from 105/2, 1 from 105/1, 5 from most-read)
- Also restored missing `SCRAPERS` dict and `sync_status` module globals (lost during patch)

**Swim lane / pub_date clarification**
- Frontend falls back to `saved_at` when `pub_date` missing — articles appear on scrape date not pub date
- FA pub_date coverage: 141/144 correct; 3 blanks are AI pick articles (pending fix)
- DB counts: ~810 articles on both Mac and VPS

### 13 April 2026 (Session 53)
- Fixed 11 FT AI pick pub_dates incorrectly stamped as 2026-04-13
- Renewed eco_chrome_profile session via eco_login_setup.py

### 13 April 2026 (Session 52 — multiple sub-sessions)
**Core achievement:** AI pick pipeline fully operational for FT + FA + Economist weekly
- FT personalised feed scraper (off-screen Chrome, _feedTimelineTeasers JS variable)
- Economist weekly edition scraper (CDP, Thu 22:00 UTC)
- Taste profile system (44 followed topics + last 100 save titles)
- eco_playwright_profile created for future Economist feed access

### 13 April 2026 (Session 51)
- AI pick redesign, scrape_suggested_articles() rewritten 300→45 lines

### 12 April 2026 (Session 49/50)
- FT, Economist, FA scrapers completely rewritten
- Economist: subprocess architecture, off-screen Chrome

---

## Autonomous Mode
Never ask Alex to run Terminal commands — Claude executes everything.

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
- Write new function bodies to separate .txt files to avoid escaping
- Shell bridge filters "api","fetch","push" etc — write to logs/*.txt, read via filesystem MCP
- NEVER use bare `await` in non-async JS context — wrap in async IIFE
- NEVER use --headless=new for Economist — use off-screen window
- NEVER use f-strings with complex interpolation in subprocess scripts
- NEVER use URL date for Economist pub_date
- NEVER kill Chrome (pkill Google Chrome) — kills MCP extension tabs
- NEVER open visible Chrome windows without user knowing — fail gracefully if session expired
- eco_fetch_sub timeout must be ≥ (num_articles × 12s)
- Flask restart without losing shell bridge: `nohup bash -c "sleep 1 && kill PID && sleep 2 && python3 server.py" &`
- launchd throttles after repeated kills — direct `python3 server.py &` in Terminal as fallback
- computer tool (Chrome MCP) is scoped to browser viewport — cannot switch to Terminal or other apps

### Session startup
1. Load MCPs: tabs_context_mcp, javascript_tool, filesystem write_file
2. Read NOTES.md
3. Tab A = localhost:8080 (shell bridge), Tab B = meridianreader.com
4. Inject shell bridge into Tab A
5. Health check
