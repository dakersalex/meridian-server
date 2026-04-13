# Meridian — Technical Notes
Last updated: 13 April 2026 (Session 53 — FT AI pick pub_date fixes, Economist session renewal)

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
- ~/meridian-server/logs/

## Mac Flask
- Restart: `lsof -ti tcp:4242 | xargs kill -9`
- CRITICAL: restart after every deploy

## Deploying
  cd ~/meridian-server && ./deploy.sh "message"

---

## Database (13 April 2026 — end of session 53)
| Source | Mac | VPS |
|---|---|---|
| FT | ~243 | ~243 |
| Economist | ~327 | ~327 |
| FA | ~139 | ~139 |
| Bloomberg | ~43 | ~43 |
| Other | ~19 | ~19 |
| **Total** | **~771** | **~771** |

AI picks in Feed (auto_saved=1): ~38
API balance: ~$9 — runway depends on AI pick frequency

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

## Foreign Affairs Scraper
- Playwright, fa_profile/, headless=True
- FA cookie expires 2026-05-23
- 11 pending unenriched on VPS — paywall-truncated stubs, need cleanup

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
6. Push articles → VPS
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
   - pub_date: from `publishedDate` field (ISO timestamp → YYYY-MM-DD) ✅ correct going forward

2. **Foreign Affairs most-read** — `foreignaffairs.com/most-read`
   - Plain HTTP fetch, no auth needed
   - pub_date: currently blank — see fix below

3. **Economist weekly edition** (Thursday nights)
   - `economist.com/weeklyedition/YYYY-MM-DD` via CDP (eco_chrome_profile)
   - Runs Thu 22:00 UTC, once per edition
   - Gate key: `ai_pick_economist_weekly_YYYY-MM-DD`
   - pub_date: edition date string ✅ correct

### pub_date known issues
- **13 FT AI picks had wrong pub_date** — ✅ FIXED in Session 53
  11 corrected via web search (Apr 7–10), 2 already correct. Pushed to VPS.
- **FA AI picks have no pub_date** — FA most-read scraper doesn't extract dates
  FIX: add pub_date to Sonnet scoring prompt response for FA articles
  (Sonnet can infer/find dates since it's already scoring them)

### Economist feed pages — NOT scraped (Cloudflare blocks all approaches)
- `economist.com/for-you/feed` and `/for-you/topics` block Playwright
- `eco_chrome_profile` can only use CDP (launch_persistent_context fails)
- Fresh profiles get Cloudflare-blocked immediately
- WORKAROUND: `eco_playwright_profile/` being built up via `eco_playwright_browse.py`
  Run that script occasionally over coming days to build browsing history
  Once Cloudflare stops blocking, switch AI pick to use that profile
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

### Known issues
- eco_chrome_profile session renewed Session 53 (13 Apr 2026)
- CRITICAL: Never leave Chrome windows open on login pages — scraper must detect
  login redirect and fail gracefully, not hang

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

### 🔴 Session 54 — do first
1. Fix FA AI picks missing pub_date:
   - Add pub_date field to Sonnet scoring prompt response for FA articles
2. FA ingestion failure — FA averaged 0.6 articles/day last 7d; zero-days on 04-08, 04-12, 04-13
   - Investigate FA scraper reliability, check cookie/session, check for Cloudflare blocks
3. Economist delivery gaps — 3 zero-days in last 7d (04-08, 04-11, 04-13); erratic daily counts
   - Check Economist bookmarks scraper logs, verify session health
4. FT backlog pending — 13 unenriched FT articles awaiting full-text enrichment
   - Check enrichment pipeline, may need manual trigger or API credit top-up

### 🔴 Priority fixes
5. Economist scraper: add login-redirect detection — fail gracefully, don't hang
6. FA 11 pending — delete paywall-truncated stubs from VPS
7. FA cookie renewal — expires 2026-05-23
8. eco_playwright_profile — continue building browsing history for Economist feed access

### 🔴 Monitor
9. Economist CDP session — renewed Session 53, monitor for next expiry

### 🟡 Planned Features
10. Daily briefing backend
11. Chat Q&A

---

## Build History

### 13 April 2026 (Session 53)

**Core achievement:** FT AI pick pub_date corrections, Economist session renewal

- Fixed 11 FT AI pick pub_dates that were incorrectly stamped as 2026-04-13
  Used web search (FT X/Twitter timestamps, OneNewsPage, syndication dates) to find real dates
  Corrected range: Apr 7–10. Updated Mac DB + pushed to VPS (11 upserted)
- Renewed eco_chrome_profile session via eco_login_setup.py
  Thursday night Economist weekly edition pick should now work
- VPS DB path confirmed as /opt/meridian-server/meridian.db (not /root/)
- Health check at session start: 6/10
  Issues: FA ingestion weak (0.6/day avg), Economist 3 zero-days, 13 FT unenriched
- DB: 771 articles (243 FT, 327 Eco, 139 FA, 43 Bloomberg, 19 other), 38 AI picks

### 13 April 2026 (Session 52 — multiple sub-sessions)

**Core achievement:** AI pick pipeline fully operational for FT + FA + Economist weekly

**52a — Initial ai_pick_feed_scrape() build**
- New function scraping FT personalised feed + FA most-read + Economist feed
- Discovered: headless=True blocked by Cloudflare on FT and Economist feed pages
- Fix: off-screen real Chrome (headless=False, --window-position=-3000,-3000)
- FT: works perfectly with ft_profile subprocess
- Economist feed (for-you/topics, for-you/feed): blocked regardless of approach
  eco_chrome_profile incompatible with launch_persistent_context (CDP profile)
  Fresh profiles hit Cloudflare immediately
  Decision: skip Economist feed for now, use weekly edition instead

**52b/c — FT subprocess refinement**
- FT visible window bug: subprocess approach keeps window off-screen correctly
- First successful run: 135-183 FT articles, 56 new per run
- Sonnet scoring initially miscalibrated (private equity scoring 10)

**52d — Taste profile system**
- Scraped FT followed topics (13) and Economist followed topics (15) from screenshots
- Built ai_pick_followed_topics (44 topics) stored in kt_meta
- Built ai_pick_taste_titles from last 100 manual saves
- Scoring prompt rewritten to use both — dramatic improvement
- Before: "Ackman fund" = 10, "OpenAI Stargate" = 1
- After: "Fed/energy surge" = 9, "OpenAI Stargate" = 7, "Ackman fund" = 7 (hedge funds topic)
- Auto-update: taste_titles updated whenever new article saved to Feed

**52e — Economist weekly edition scraper**
- Tested economist.com/weeklyedition/2026-04-11 via CDP: 73 articles, no Cloudflare
- Built ai_pick_economist_weekly() — CDP scrape + Sonnet scoring
- Thursday 22:00 UTC scheduler slot added
- Edition date logic: last Saturday Mon-Wed, next Saturday Thu(after 20UTC)/Fri/Sat
- Gate: once per edition keyed by edition date

**52f — pub_date fixes**
- Discovered _feedTimelineTeasers JS variable on FT feed page
  Contains: title, URL, publishedDate (ISO), standfirst, isOpinion, isPodcast flags
  Much better than DOM scraping — accurate dates, richer metadata
- Updated FT scraper to use _feedTimelineTeasers (correct going forward)
- Backfilled 13 blank pub_dates using saved_at as fallback — WRONG (all show 13 Apr)
  Fixed in Session 53: web_search to find actual publication dates, all 11 corrected + pushed to VPS

**52 — Other**
- Removed redundant Flask scrape triggers (Session 51d carried forward)
- eco_playwright_profile created for future Economist feed access
  Needs more browsing history before Cloudflare stops blocking

### 13 April 2026 (Session 51)
- AI pick redesign patches applied (score >=9, twice-daily gate)
- Removed redundant Flask scrape triggers (bot detection risk)
- scrape_suggested_articles() rewritten — 300 lines → 45 lines
- Settled on feed-scraping + Sonnet approach

### 12 April 2026 (Session 49/50)
- FT, Economist, FA scrapers completely rewritten
- Economist: subprocess architecture, off-screen Chrome
- Newsletter timing gap fixed

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
- Shell bridge filters "api","fetch" etc — write to tmp_*.txt, read via filesystem MCP
- NEVER use bare `await` in non-async JS context — wrap in async IIFE
- NEVER use --headless=new for Economist — use off-screen window
- NEVER use f-strings with complex interpolation in subprocess scripts
- NEVER use URL date for Economist pub_date
- NEVER kill Chrome (pkill Google Chrome) — kills MCP extension tabs
- NEVER open visible Chrome windows without user knowing — fail gracefully if session expired
- eco_fetch_sub timeout must be ≥ (num_articles × 12s)

### Session startup
1. Load MCPs: tabs_context_mcp, javascript_tool, filesystem write_file
2. Read NOTES.md
3. Tab A = localhost:8080 (shell bridge), Tab B = meridianreader.com
4. Inject shell bridge into Tab A
5. Health check
