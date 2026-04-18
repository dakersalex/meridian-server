# Meridian — Technical Notes
Last updated: 18 April 2026 (Session 59 — Batch API enrichment + performance fix)

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

## Batch API Enrichment (Session 59)

### Architecture
- **Script:** `batch_enrichment_final.py` — 50% cost savings vs real-time API calls
- **Model:** `claude-sonnet-4-6` (alias auto-updates to latest Sonnet 4.6)
- **Processing:** <2 minutes for 42 articles (vs 24h SLA)
- **Status:** All 42 requests succeeded, ready for DB update

### Results parsing
- **Success format:** `result.type === "succeeded"`
- **Content path:** `result.message.content[0].text` 
- **Markdown wrapper:** Remove ```json fences before JSON.parse()
- **Database:** Combine into existing `summary` field

## Database (18 April 2026 — Session 59)
| Source | Mac | VPS |
|---|---|---|
| FT | ~314 | ~319 |
| Economist | ~366 | ~366 |
| FA | ~157 | ~169 |
| Bloomberg | ~43 | ~45 |
| Other | ~19 | ~46 |
| **Total** | **~899** | **~945** |

Title-only backlog: 42 articles processed via Batch API

## Outstanding Issues / Next Sessions

### 🔴 Session 60 — do first
1. **Complete batch enrichment** — Run `reprocess_batch_results_fixed.py` to update 42 articles
2. **VPS sync** — Push enriched articles via `vps_push.py`
3. **FT backlog** — 36 remaining title_only FT articles

## Build History

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
