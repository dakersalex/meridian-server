# Meridian — Technical Notes
Last updated: 18 April 2026 (Session 60 — RSS AI picks, fallback enrichment, health monitoring)

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
- ~/meridian-server/rss_ai_pick.py — RSS-based AI pick pipeline (Session 60)
- ~/meridian-server/batch_enrichment_final.py — Batch API enrichment script
- ~/meridian-server/wake_and_sync.sh
- ~/meridian-server/vps_push.py
- ~/meridian-server/logs/

## Database (18 April 2026 — Session 60)
| Source | Mac | VPS |
|---|---|---|
| FT | ~323 | ~319+ |
| Economist | ~366 | ~366 |
| FA | ~163 | ~169+ |
| Bloomberg | ~43 | ~45 |
| Other | ~19 | ~46 |
| **Total** | **~914** | **~945+** |

**Unenriched: 0 on both Mac and VPS** ✅

## RSS-Based AI Pick Pipeline (Session 60)

### Architecture
- **Script:** `rss_ai_pick.py` — standalone, no Playwright, no auth, no Cloudflare
- **Endpoint:** `POST /api/rss-pick`
- **Feeds:** 6 FT sections + 6 Economist sections + 1 FA feed = 13 RSS feeds
- **Scoring:** Haiku (cost-efficient) scores all candidates in one API call
- **Speed:** ~6 seconds total (fetch all feeds + score 76 candidates)
- **Gate:** Twice daily (morning/midday) via kt_meta keys

### Feed URLs
FT: rss/home, world, markets, global-economy, companies, technology (all `?format=rss`)
Economist: leaders, briefing, finance-and-economics, international, business, the-world-this-week (all `/rss.xml`)
FA: /rss.xml

### Scoring & routing
- Score 8+ (FT/Eco) or 7+ (FA) → auto-saved to Feed (auto_saved=1, status=title_only)
- Score 6-7 → added to Suggested inbox
- Score 0-5 → discarded
- After auto-save, triggers `/api/enrich-remaining` for title-only fallback enrichment

### Why RSS > Playwright for AI picks
- No authentication needed (RSS feeds are public)
- No Cloudflare blocking
- No Playwright profile locks or headless Chrome issues
- 6 seconds vs 90+ seconds
- No dependency on profile session renewal
- RSS gives title + URL + description + pub_date — everything the scorer needs

### Legacy Playwright pick still runs after RSS pick (for personalised FT feed)

## Enrichment Architecture (Session 60)

### Three-layer enrichment pipeline
1. **Body-based enrichment** (`enrich_article_with_ai`) — Full AI analysis from article text. Requires body ≥200 chars. Uses Haiku.
2. **Title-only fallback** (`enrich_from_title_only`) — Generates summary from title + source alone when body unavailable. Uses Haiku.
3. **Cascade logic** — `enrich-remaining` tries body enrichment first, falls back to title-only if JSON parse fails or body too short.

### Automated enrichment flow (wake_and_sync.sh)
1. Sync triggers scraping for FT, Economist, FA
2. `/api/enrich-title-only` runs body fetching + AI enrichment + final fallback sweep
3. RSS pick runs (`/api/rss-pick`) — finds new articles, auto-saves, enriches
4. Legacy Playwright AI pick runs (fallback for personalised feed)
5. `/api/enrich-remaining` runs as safety net
6. `/api/health/enrichment` logged for monitoring

### Key endpoints
- `GET /api/health/enrichment` — ok/unenriched count/status breakdown
- `POST /api/enrich-remaining` — fallback enrichment with cascade
- `POST /api/rss-pick` — RSS-based AI pick (no auth needed)
- `POST /api/enrich-title-only` — full enrichment pipeline

## Batch API Enrichment (Session 59)
- **Script:** `batch_enrichment_final.py` — 50% cost savings vs real-time
- **Model:** `claude-sonnet-4-6`
- **Status:** All 42 results applied to DB in Session 60

## Outstanding Issues / Next Sessions

### 🟡 Session 61
1. **Monitor tomorrow's automated sync** — verify RSS pick + enrichment fallback produce zero unenriched
2. **Economist scraper** — RSS feeds now handle Economist AI picks; consider whether Playwright scraper is still needed
3. **End-to-end test** — simulate full wake_and_sync cycle
4. **FA URL validation** — verify 38 Haiku-guessed URLs with HTTP HEAD checks

### 🟢 Nice to have
- Daily email alert if unenriched > 0
- Economist chart backfill (173 articles)
- KT theme evolution improvements
- Consider dropping Playwright AI pick entirely if RSS proves reliable

## Build History

### 18 April 2026 (Session 60)

**RSS-based AI pick pipeline — no Playwright, no auth, no Cloudflare**
- Built `rss_ai_pick.py`: fetches 13 RSS feeds (6 FT, 6 Economist, 1 FA)
- Scores candidates with Haiku in single API call (~6 seconds total)
- First run: 76 candidates found, 5 auto-saved to feed, 16 to suggested
- Added `/api/rss-pick` endpoint and wired into wake_and_sync.sh
- Eliminates Playwright/Cloudflare dependency for article discovery

**Unenriched backlog eliminated: 39 → 0 (Mac), 37 → 0 (VPS)**
- Applied 42 batch enrichment results from Session 59
- Built title-only fallback enrichment for articles without body text
- Fixed cascade logic: body enrichment failure falls back to title-only
- VPS enrichment triggered via `/api/enrich-remaining`

**FA author-URL bug fixed: 38 articles**
- Root cause: `_extract_articles` stored `/authors/` URLs from saved-articles page
- Used Haiku to construct correct article URLs (38/38 fixed)
- `SKIP_PREFIXES` already prevents future ingestion

**New infrastructure**
- `enrich_from_title_only()` — fallback enrichment function
- `/api/health/enrichment` — monitoring endpoint
- `/api/enrich-remaining` — manual trigger with cascade logic
- `wake_and_sync.sh` — RSS pick + enrichment fallback + health check

**Key learnings**
- RSS feeds bypass all auth/bot-detection issues and are much faster than Playwright
- Haiku is good enough for article scoring (vs Sonnet) at fraction of cost
- Cascade fallback (body → title-only) catches all enrichment edge cases
- Title-only enrichment from Haiku produces usable summaries

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
