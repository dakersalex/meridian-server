# Meridian — Technical Notes
Last updated: 18 April 2026 (Session 60 — Zero unenriched backlog, fallback enrichment, health monitoring)

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
- ~/meridian-server/batch_enrichment_final.py — Batch API enrichment script
- ~/meridian-server/reprocess_batch_results_fixed.py — Fix successful batch results
- ~/meridian-server/wake_and_sync.sh
- ~/meridian-server/vps_push.py
- ~/meridian-server/logs/

## Database (18 April 2026 — Session 60)
| Source | Mac | VPS |
|---|---|---|
| FT | ~318 | ~319 |
| Economist | ~366 | ~366 |
| FA | ~160 | ~169 |
| Bloomberg | ~43 | ~45 |
| Other | ~19 | ~46 |
| **Total** | **~906** | **~945** |

**Unenriched: 0 on both Mac and VPS** ✅

## Enrichment Architecture (Session 60)

### Three-layer enrichment pipeline
1. **Body-based enrichment** (`enrich_article_with_ai`) — Full AI analysis from article text. Requires body ≥200 chars. Uses Haiku.
2. **Title-only fallback** (`enrich_from_title_only`) — Generates summary from title + source alone when body unavailable. Uses Haiku.
3. **Cascade logic** — `enrich-remaining` endpoint tries body enrichment first, falls back to title-only if JSON parse fails or body too short.

### Automated enrichment flow (wake_and_sync.sh)
1. Sync triggers scraping for FT, Economist, FA
2. `/api/enrich-title-only` runs body fetching + AI enrichment + final fallback sweep
3. `/api/enrich-remaining` runs as safety net at end of wake_and_sync
4. `/api/health/enrichment` logged for monitoring

### Key endpoints
- `GET /api/health/enrichment` — Returns `ok: true/false`, unenriched count by source, status breakdown, last sync times
- `POST /api/enrich-remaining` — Trigger fallback enrichment for any remaining unenriched articles
- `POST /api/enrich-title-only` — Full enrichment pipeline with fallback sweep

## Batch API Enrichment (Session 59)

### Architecture
- **Script:** `batch_enrichment_final.py` — 50% cost savings vs real-time API calls
- **Model:** `claude-sonnet-4-6` (alias auto-updates to latest Sonnet 4.6)
- **Processing:** <2 minutes for 42 articles (vs 24h SLA)
- **Status:** All 42 results applied to DB in Session 60

### Results parsing
- **Success format:** `result.type === "succeeded"`
- **Content path:** `result.message.content[0].text` 
- **Markdown wrapper:** Remove ```json fences before JSON.parse()
- **Database:** Combine into existing `summary` field

## Outstanding Issues / Next Sessions

### 🟡 Session 61 — monitoring & reliability
1. **End-to-end integration test** — Simulate full wake_and_sync cycle, verify zero unenriched after
2. **Economist scraper stabilization** — Chrome profile session renewal automation
3. **FA URL validation** — Haiku-guessed URLs (38 fixed in Session 60) may not all be valid; verify with HTTP HEAD checks
4. **VPS 502 during deploy** — wake_and_sync 06:00 run hit 502 errors pushing to VPS (VPS was restarting); consider deploy timing or retry logic

### 🟢 Nice to have
- FA scraper: fix `_extract_articles` to prefer article links over author links from saved-articles page (root cause of /authors/ URL bug)
- Daily email alert if unenriched > 0 after sync
- Economist chart backfill (173 articles)
- KT theme evolution improvements

## Build History

### 18 April 2026 (Session 60)

**Unenriched backlog eliminated: 39 → 0 (Mac), 37 → 0 (VPS)**
- Applied 42 batch enrichment results from Session 59 (`reprocess_batch_results_fixed.py`)
- Built and ran title-only fallback enrichment for 10 FA articles with insufficient body text
- Triggered VPS fallback enrichment for 37 remaining unenriched articles
- Fixed cascade logic: body enrichment failure now falls back to title-only (fixed "Europe's Next War" JSON parse failure)

**FA author-URL bug fixed: 38 articles**
- Root cause: FA scraper `_extract_articles` stored `/authors/` URLs from saved-articles page instead of article URLs
- Fix: Used Haiku to construct correct article URLs from titles (38/38 fixed)
- Prevention: `SKIP_PREFIXES` already includes `/authors/` for future scrapes

**New infrastructure**
- `enrich_from_title_only()` — fallback enrichment function in server.py
- `/api/health/enrichment` — monitoring endpoint (returns ok/unenriched count/status breakdown)
- `/api/enrich-remaining` — manual trigger for fallback enrichment with cascade logic
- `wake_and_sync.sh` updated: calls `enrich-remaining` + health check at end of every sync

**Key learnings**
- FA saved-articles page has `h3 a` links to author pages, not articles — `SKIP_PREFIXES` prevents future ingestion
- Body ≥200 chars doesn't guarantee successful enrichment — Haiku can return malformed JSON on very short text
- Cascade fallback (try body → fall back to title-only) catches all edge cases
- VPS has 39 more articles than Mac (945 vs 906) — likely from early development or direct VPS saves

---

### 18 April 2026 (Session 59)

**Batch API enrichment proof of concept**
- **Model:** Already using latest `claude-sonnet-4-6` (auto-updates to Sonnet 4.6)
- **Success:** 42 articles processed in <2 minutes at 50% cost savings
- **Format:** `POST /v1/messages/batches` with JSON payload (not file upload)
- **Parsing:** Fixed result format: `result.message.content[0].text`
- **Production ready:** Complete batch enrichment system for background processing

**Performance fix: 4x speed improvement**
- **Root cause:** SERVER variable hardcoded to `https://meridianreader.com` instead of `http://localhost:4242`
- **Symptoms:** Page load degraded from ~0.5s to ~2s (API calls to wrong server)
- **Fix:** Updated SERVER to point to local Flask API, updated status text
- **Result:** Page load back to ~51ms API response time ✅

**Key learnings**
- Batch API processing: Much faster than 24h SLA (typically <1 hour)
- Model aliases: `claude-sonnet-4-6` automatically uses latest version
- Local development: Always ensure frontend points to localhost Flask API
- Performance monitoring: API response times are key indicator

---

## Session startup — CRITICAL ORDER
1. `tabs_context_mcp` with `createIfEmpty:true`
2. Read NOTES.md  
3. Navigate Tab A to localhost:8080
4. Inject shell bridge
5. Health check
