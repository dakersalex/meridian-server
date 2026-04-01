# Meridian — Technical Notes
Last updated: 1 April 2026 (Session 30 — complete)

## Overview
Personal news aggregator. Flask API + SQLite backend now running on Hetzner VPS (always-on).
Frontend served via nginx with HTTPS. Accessible from anywhere at https://meridianreader.com/meridian.html

## Domain
- Domain: meridianreader.com (Namecheap, expires Mar 26 2027)
- DNS: A records @ and www → 204.168.179.158
- SSL: Let's Encrypt via Certbot (auto-renews)

## Infrastructure
- VPS: Hetzner CPX22, Helsinki, €7/mo (incl. backups)
- IP: 204.168.179.158
- OS: Ubuntu 24.04
- SSH: ssh root@204.168.179.158 (key: ~/.ssh/id_ed25519)
- Flask service: systemd (auto-starts, auto-restarts)
- HTTP: nginx on port 80 (redirects to HTTPS)
- HTTPS: nginx on port 443
- nginx config: /etc/nginx/sites-available/meridian
  - meridian.html served with Cache-Control: no-cache
  - sw.js served with Cache-Control: no-cache
- GitHub: https://github.com/dakersalex/meridian-server (public)

## File Locations (VPS)
- /opt/meridian-server/server.py       — Flask API (port 4242)
- /opt/meridian-server/meridian.html   — Main frontend
- /opt/meridian-server/meridian.db     — SQLite database
- /opt/meridian-server/credentials.json — Anthropic API key + FA login
- /opt/meridian-server/venv/           — Python virtualenv (not in git)

## File Locations (Mac — local dev only)
- ~/meridian-server/server.py          — Flask API
- ~/meridian-server/meridian.html      — Main frontend
- ~/meridian-server/meridian.db        — Local database (not synced to VPS)
- ~/meridian-server/credentials.json   — Anthropic API key
- ~/meridian-server/cookies.json       — Publication session cookies
- ~/meridian-server/newsletter_sync.py — iCloud IMAP newsletter poller
- ~/meridian-server/extension/         — Chrome extension v1.3
- ~/meridian-server/brief_pdf.py       — Intelligence brief PDF generation module
- ~/meridian-server/logs/              — Server and sync logs
- ~/Library/LaunchAgents/com.alexdakers.meridian.plist       — Auto-start Flask (Mac)
- ~/Library/LaunchAgents/com.alexdakers.meridian.http.plist  — Auto-start HTTP (Mac)
- ~/Library/LaunchAgents/com.alexdakers.meridian.sync.plist  — Auto-start sync (Mac)

## Daily Use
Open in browser (any device, any network):
https://meridianreader.com/meridian.html

Mac local (if needed):
http://localhost:8080/meridian.html

## VPS Management
SSH in: ssh root@204.168.179.158
Check Flask: systemctl status meridian
Restart Flask: systemctl restart meridian
Check nginx: systemctl status nginx
Restart nginx: systemctl reload nginx
View logs: journalctl -u meridian -f

## Deploying Code Updates
One command from Mac Terminal:
  cd ~/meridian-server && ./deploy.sh "description"

(deploy.sh: git add -A, commit, push, SSH pull on VPS, systemctl restart meridian)

## Database (1 April 2026)
Total: ~508 articles (Mac), ~508 articles (VPS)
- Financial Times: 153 / The Economist: 257 / Foreign Affairs: 46 / Bloomberg: 38 / Other: ~14

## Intelligence Brief Pipeline (Session 30 — FULLY WORKING ✅)

### Overview
- brief_pdf.py — standalone module, ReportLab + Pillow, generates A4 PDF
- Single Sonnet call: text generated once, used for both modal display and PDF build
- Full brief includes Economist charts (subtopic sections only); short brief is text only
- Pillow installed: Mac + VPS venv

### User flow
1. Click "Short Brief" or "Full Intelligence Brief" on any theme
2. Modal opens with progress spinner — rotating step labels + elapsed seconds
3. ~60-90s later text brief renders in modal (Executive Summary in amber panel)
4. "Open as PDF ↗" button top-right opens the PDF in a new tab
5. PDF is built from the same text (no second Sonnet call) with charts embedded

### Single-call architecture (Session 30)
- Frontend polls /api/kt/brief for text; once done, passes text to /api/kt/brief/pdf
- PDF job receives pregenerated_text, skips Sonnet call, builds PDF directly
- Modal and PDF always show identical content
- Saves ~60s and one full Sonnet call per brief generation

### Prompt design (_build_prompt in brief_pdf.py)
- Fully domain-agnostic — works across all 10 themes (geopolitics, markets, AI, corporate, etc.)
- Statistics instruction: "incorporate specific figures, percentages, prices, quantities or dates
  from the source articles — one or two per section to anchor the assessment.
  Do not invent or estimate statistics; only use figures present in the articles."
- Section instruction: "Lead with key finding, support with figures, close with implication"
- Explicitly bans title heading and overview section
- No Source Notes section (was generating synthetic/hallucinated attribution)

### Article context (_build_article_context in brief_pdf.py)
- Passes SOURCE + TITLE + SUMMARY + first 400 chars of EXCERPT per article
- Body excerpt preserves specific statistics that get lost in summary-only context
- Max 60 articles for full brief, 30 for short

### Chart image processing (_crop_economist_chart in brief_pdf.py)
- Background whitening: (236, 235, 223) beige → (255, 255, 255) white, ±18 tolerance
  Uses numpy vectorised operation for speed across 14 charts per brief
- Bottom crop: scans upward for first all-white separator band, crops there
  (removes "CHART: THE ECONOMIST" / "MAP: THE ECONOMIST" label)
- Top crop: detects end of title text block, crops to chart data start
  (removes Economist bold title + red accent bar + subtitle)
- Falls back gracefully if Pillow/numpy unavailable
- Pillow confirmed present: Mac (system) and VPS venv

### Figure numbering and captions
- Consecutive Figure 1, 2, 3… numbering across the full brief in reading order
- Caption below each image: "Figure N — [title derived from description]"
- Title extracted from first clause of Haiku description field (≤65 chars)
- Caption style: small italic grey (Helvetica-Oblique, 8pt)
- Never a solo chart — always pairs (2 per row); if only 1 qualifies, section gets 0

### Chart selection rules
- No charts in: Executive Summary, Overview, Cross-cutting Themes, Strategic Implications,
  Watch List, Key Developments, Source Notes
- Cross-brief similarity dedup: >50% description token overlap → rejected
- Both images in a pair normalised to same height (prevents cropping/misalignment)
- Budget: up to 2 per section, global cap 14

### Flask routes
- POST /api/kt/brief — text brief (async), returns {ok, job_id}
- GET /api/kt/brief/status/<job_id> — poll {status, brief, error}
- POST /api/kt/brief/pdf — PDF job (async), accepts optional {text} field
- GET /api/kt/brief/pdf/status/<job_id> — poll {status, ready, size, error}
- GET /api/kt/brief/pdf/download/<job_id> — serve completed PDF

### Key learnings
- NEVER write brief_pdf.py via heredoc — always use filesystem:write_file
- Patch scripts must use binary-safe replacements for JS regex patterns
- Pillow's numpy path is fast enough for 14 chart images per brief generation

## Economist Chart & Map Capture (Session 26 ✅)

### article_images DB schema
```sql
CREATE TABLE IF NOT EXISTS article_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id TEXT NOT NULL,
    caption TEXT NOT NULL,
    description TEXT DEFAULT '',
    insight TEXT DEFAULT '',
    image_data BLOB NOT NULL,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    captured_at INTEGER NOT NULL,
    mac_id INTEGER DEFAULT NULL
)
```
mac_id = Mac autoincrement PK, used for dedup (all captions are "chart: the economist")

### DB state (1 April 2026)
- Mac: 153 images, 153 with insight
- VPS: 153 images (87 legacy rows deleted Session 29)
- description: visual description (25 words, Haiku at capture time)
- insight: analytical point the chart supports (30 words, enriched separately)

### Image sync to VPS
- POST /api/push-images — receives images from Mac, upserts on mac_id
- wake_and_sync.sh pushes images on every sync
- reportlab and Pillow installed in VPS venv

## Autonomous Mode (Claude in Chrome + shell endpoint)

### Shell bridge
```js
window.shell = (cmd) => fetch('http://localhost:4242/api/dev/shell', {
  method:'POST', headers:{'Content-Type':'application/json'},
  body:JSON.stringify({cmd})
}).then(r=>r.json());
```

### MCP setup
- Filesystem MCP: read/write ~/meridian-server/
- Claude in Chrome MCP: browser tab control
- Tab A (localhost:8080/meridian.html): shell bridge
- Tab B (meridianreader.com/meridian.html): live site verification
- TabIds change every session — always call tabs_context_mcp first

### NEVER restart Flask via shell endpoint — it kills itself mid-request

### Session start health check
```js
window.shell(`
  echo '=== Flask ===' && curl -s http://localhost:4242/api/health &&
  echo '=== DB ===' && sqlite3 ~/meridian-server/meridian.db "SELECT source, COUNT(*), SUM(status='title_only') as pending FROM articles GROUP BY source" &&
  echo '=== KT ===' && curl -s http://localhost:4242/api/kt/status &&
  echo '=== Images ===' && curl -s http://localhost:4242/api/images/backfill/status
`).then(d => console.log('HEALTH:', d.stdout));
```

### Dangerous operations checklist
Before any DELETE/UPDATE: SELECT preview first, state what will be affected, then execute.
Lesson: Session 19 deleted all user bookmarks assuming they were junk.

### Key patterns
- Write files via filesystem:write_file (never heredoc)
- VPS Python: write script → scp → run (never inline -c strings)
- After deploy: nginx no-cache means hard refresh always gets latest
- JS regex corruption: patch scripts must not embed literal \n inside regex literals

## Service Worker
- sw.js cache version: meridian-v5
- nginx: no-cache for meridian.html and sw.js
- If stuck: DevTools → Application → Service Workers → Unregister → hard refresh

## Schedule (Geneva/CEST)
- 05:40 / 11:40 — Mac syncs FT + Economist + FA via Playwright
- 05:50 / 11:50 — VPS scores, agent auto-saves 8+ to Feed
- 23:00 — DB backup to VPS (7 days retained)

## Next Steps (priority order)
1. **PWA icons** — proper 192×192 and 512×512
2. **Newsletter auto-sync** — newsletter_sync.py gitignored; VPS cannot auto-sync
3. **Clean up tmp_ files** — many tmp_*.py committed during Sessions 28-30
4. **Charts in modal** — currently text only; charts only in PDF (deferred, not a blocker)
5. **Chart crop tuning** — verify top/bottom crop thresholds work well across all chart types
   (maps, bar charts, line charts, scatter plots) — adjust _BG_TOLERANCE / thresholds if needed

## Build History
### 1 April 2026 (Session 30)
- Single Sonnet call architecture: text generated once, passed to PDF job (d76300c2)
- Unified prompt via _build_prompt(): domain-agnostic, statistics instruction, no Source Notes
- Richer article context via _build_article_context(): summary + 400-char body excerpt
- Chart image processing: background whitening (beige→white), bottom label crop,
  top title crop, Figure N captions, consecutive numbering (0c41c433, 41c8cf95)
- Pillow numpy vectorised background replacement confirmed working on Mac + VPS

### 1 April 2026 (Session 29)
- Brief modal: text preview + "Open as PDF ↗" replacing auto-download
- Progress ticker during generation (rotating steps + elapsed time)
- brief_pdf.py: no solo charts, cross-brief dedup, aligned heights, no overview section
- sw.js fixed (was empty on VPS), cache bumped to v5, nginx no-cache headers
- JS regex corruption fixed (literal newlines in patch scripts)

### 31 March 2026 (Session 28)
- brief_pdf.py rewritten from scratch, PDF pipeline end-to-end
- article_images sync Mac→VPS, mac_id dedup, 153 images pushed

### Earlier sessions (26-27)
- Economist chart capture, insight enrichment, KT themes, article grid

## GitHub Visibility
- Repo: PUBLIC — github.com/dakersalex/meridian-server
- Excluded: credentials.json, cookies.json, meridian.db, newsletter_sync.py, venv/

## Session Starter Prompt
---
You are helping me build Meridian, my personal news aggregator. Please read my technical notes from the Filesystem MCP at /Users/alexdakers/meridian-server/NOTES.md and review them. Then run the session start health check.
---

Note for Claude: Read NOTES.md via Filesystem MCP (NOT GitHub URL — blocked). Check Flask via shell endpoint before proceeding. Never restart Flask via the shell endpoint.
