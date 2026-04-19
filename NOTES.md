# Meridian — Technical Notes
Last updated: 19 April 2026 (Session 61 — swim lane fix, extension body-fetcher live)

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
- ~/meridian-server/rss_ai_pick.py — RSS-based AI pick pipeline
- ~/meridian-server/extension/ — Chrome extension v1.3 with background body-fetcher
- ~/meridian-server/batch_enrichment_final.py — Batch API enrichment script
- ~/meridian-server/wake_and_sync.sh
- ~/meridian-server/vps_push.py
- ~/meridian-server/logs/

## Database (19 April 2026 — Session 61)
| Source | Mac | VPS |
|---|---|---|
| FT | ~323 | ~319+ |
| Economist | ~366 | ~366 |
| FA | ~163 | ~169+ |
| Bloomberg | ~43 | ~45 |
| Other | ~19 | ~46 |
| **Total** | **~918** | **~957** |

**Title-only (pending body fetch): 34 on Mac, being processed by extension**

## How Articles Get Into Meridian

### 1. Manual saves (Chrome extension clip button)
- You read an article → click clip → extension extracts full body text → saves to DB
- Most reliable path, always produces full_text with real summaries
- Works for all sources including Bloomberg

### 2. RSS AI picks (rss_ai_pick.py)
- Runs twice daily via wake_and_sync.sh
- Fetches 13 RSS feeds (6 FT, 6 Economist, 1 FA) — public, no auth
- Haiku scores candidates; score ≥8 (FT/Eco) or ≥7 (FA) → auto-saved as title_only
- Score 6-7 → Suggested inbox
- ~6 seconds total, no Playwright/Cloudflare issues

### 3. Extension background body-fetcher (NEW — Session 60/61)
- Every 15 minutes, checks `/api/articles/pending-body` for title_only articles
- Opens each URL in a background Chrome tab (uses YOUR logged-in session)
- Extracts body text, PATCHes article, triggers AI enrichment
- Bypasses paywalls because it uses real browser with real auth
- 5 articles per cycle

### 4. Playwright scrapers (legacy, partially broken)
- FT: headless blocked by paywall (body fetch fails, gets titles only)
- Economist: Cloudflare blocks, unreliable
- FA: works intermittently
- Still runs in wake_and_sync.sh but RSS picks + extension fetcher are the primary path now

### 5. Legacy Playwright AI pick (under evaluation)
- Scrapes personalised FT feed via _feedTimelineTeasers JS variable
- Uses Sonnet for scoring (more expensive than Haiku)
- Requires ft_profile Playwright session + 5-min wait
- Still runs after RSS pick as fallback — evaluate whether to remove

## Enrichment Pipeline

### How articles get enriched (body → summary)
- `enrich_article_with_ai()` — sends body text (≥200 chars) to Haiku for summary, tags, topic
- Only works with REAL article body text — no fake/imagined summaries
- `enrich_from_title_only()` was removed (Session 60) — never generate summaries without real text

### Automated flow (wake_and_sync.sh)
1. Playwright sync (FT/Economist/FA) → fetches body where possible → enriches
2. RSS pick → discovers new articles → saves as title_only
3. Legacy Playwright AI pick (fallback)
4. Extension body-fetcher runs independently every 15 min

### Key endpoints
- `GET /api/health/enrichment` — ok/unenriched count/status breakdown
- `GET /api/articles/pending-body` — returns title_only articles for extension body-fetcher
- `POST /api/rss-pick` — RSS-based AI pick
- `POST /api/enrich-title-only` — body fetching + enrichment pipeline

## Outstanding Issues / Next Sessions

### 🟡 Session 62
1. **Evaluate legacy Playwright AI pick** — compare RSS pick coverage vs personalised FT feed picks over 3-5 days. If RSS catches the same articles, remove the Playwright AI pick entirely (eliminates profile lock risk, 5-min sleep, Sonnet cost).
2. **Economist scraper** — RSS feeds now handle Economist AI picks; decide whether Playwright scraper is still needed for saved-article sync
3. **Extension body-fetcher monitoring** — verify it continues to clear title_only backlog reliably. Currently 34 pending.
4. **FA URL validation** — verify 38 Haiku-guessed URLs with HTTP HEAD checks
5. **pub_date normalization** — legacy Playwright AI pick stores ISO timestamps; either normalize in that code path or remove it

### 🟢 Nice to have
- Daily email alert if title_only count stays >0 for 24h
- Economist chart backfill (173 articles)
- KT theme evolution improvements

## Build History

### 19 April 2026 (Session 61)

**Swim lane date matching fix**
- Root cause: swim lane used strict equality (`===`) to match pub_date against `YYYY-MM-DD`, but AI pick articles had ISO timestamps like `2026-04-18T04:00:04.363Z`
- Fix: changed to `.substring(0,10)` comparison
- Normalized 19 existing pub_dates from ISO to YYYY-MM-DD in Mac DB
- 6 AI pick articles were invisible on April 18 bar — now visible

**Extension body-fetcher verified working**
- First batch: 5 articles fetched with real body text (3,800–28,000 chars)
- All 5 got real AI summaries from actual article content
- Title_only count dropped from 46 → 34, continuing to process

**Fake enrichment cleanup (late Session 60)**
- Removed `enrich_from_title_only()` function — no more AI-imagined summaries
- Reverted 42 articles on Mac and 32 on VPS that had fake summaries
- Policy: articles without real body text stay as title_only until extension fetches them

---

### 18 April 2026 (Session 60)

**RSS-based AI pick pipeline**
- Built `rss_ai_pick.py`: 13 RSS feeds, Haiku scoring, ~6 seconds total
- First run: 76 candidates, 5 auto-saved, 16 to suggested
- Wired into wake_and_sync.sh

**Extension background body-fetcher**
- Added to background.js: 15-min alarm, opens background tabs, extracts body
- Server endpoint `/api/articles/pending-body` returns title_only articles
- Uses real Chrome session — bypasses all paywalls

**Enrichment health monitoring**
- `/api/health/enrichment` endpoint
- Logged at end of every wake_and_sync run

---

### 18 April 2026 (Session 59)
**Batch API enrichment proof of concept**
- 42 articles processed in <2 minutes at 50% cost savings
- Performance fix: 4x speed from fixing SERVER variable

---

## Session startup — CRITICAL ORDER
1. `tabs_context_mcp` with `createIfEmpty:true`
2. Read NOTES.md
3. Navigate Tab A to localhost:8080
4. Inject shell bridge
5. Health check
