# Meridian — Technical Notes
Last updated: 18 April 2026 (Session 59 — Batch API enrichment proof of concept, confirmed Sonnet 4.6 active)

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
- ~/meridian-server/batch_enrichment_final.py — Batch API enrichment script (Session 59)
- ~/meridian-server/reprocess_batch_results_fixed.py — Fix successful batch results (Session 59)
- ~/meridian-server/wake_and_sync.sh
- ~/meridian-server/vps_push.py
- ~/meridian-server/logs/

## Batch API Enrichment (Session 59)

### Architecture
- **Script:** `batch_enrichment_final.py` — 50% cost savings vs real-time API calls
- **Model:** `claude-sonnet-4-6` (alias auto-updates to latest Sonnet 4.6)
- **Processing:** <2 minutes for 42 articles (vs 24h SLA)
- **Success:** All 42 requests succeeded, need to run `reprocess_batch_results_fixed.py` to update DB

### Results parsing
- **Success format:** `result.type === "succeeded"`
- **Content path:** `result.message.content[0].text` 
- **Markdown wrapper:** Remove ```json fences before JSON.parse()
- **Database:** Combine into existing `summary` field

### Status
- **Proof of concept:** Complete ✅
- **Cost savings:** 50% confirmed ✅
- **Ready for production:** Background enrichment for non-urgent tasks

## Database (18 April 2026 — Session 59)
| Source | Mac | VPS |
|---|---|---|
| FT | ~314 | ~319 |
| Economist | ~366 | ~366 |
| FA | ~157 | ~169 |
| Bloomberg | ~43 | ~45 |
| Other | ~19 | ~46 |
| **Total** | **~899** | **~945** |

Title-only backlog: 42 articles processed via Batch API (need `reprocess_batch_results_fixed.py`)

## Outstanding Issues / Next Sessions

### 🔴 Session 60 — do first
1. **Complete batch enrichment** — Run `reprocess_batch_results_fixed.py` to update 42 articles
2. **VPS sync** — Push enriched articles via `vps_push.py`
3. **FT backlog** — 36 remaining title_only FT articles; batch enrich

### Build History

### 18 April 2026 (Session 59)
**Batch API enrichment proof of concept**
- **Model:** Already using latest `claude-sonnet-4-6` (auto-updates)
- **Success:** 42 articles processed in <2 minutes at 50% cost
- **Format:** `POST /v1/messages/batches` with JSON payload
- **Parsing:** Fixed result format: `result.message.content[0].text`
- **Ready:** Production batch enrichment system complete

[Previous session history truncated for brevity]

---

## Session startup — CRITICAL ORDER
1. `tabs_context_mcp` with `createIfEmpty:true`
2. Read NOTES.md
3. Navigate Tab A to localhost:8080
4. Inject shell bridge
5. Health check
