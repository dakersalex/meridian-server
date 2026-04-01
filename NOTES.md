# Meridian — Technical Notes
Last updated: 1 April 2026 (Session 31 — complete)

## Overview
Personal news aggregator. Flask API + SQLite backend running on Hetzner VPS (always-on).
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
- /opt/meridian-server/brief_pdf.py    — Intelligence brief PDF generation
- /opt/meridian-server/venv/           — Python virtualenv (not in git)

## File Locations (Mac — local dev only)
- ~/meridian-server/server.py          — Flask API
- ~/meridian-server/meridian.html      — Main frontend
- ~/meridian-server/meridian.db        — Local database (not synced to VPS)
- ~/meridian-server/credentials.json   — Anthropic API key
- ~/meridian-server/cookies.json       — Publication session cookies
- ~/meridian-server/brief_pdf.py       — Intelligence brief PDF generation module
- ~/meridian-server/newsletter_sync.py — iCloud IMAP newsletter poller
- ~/meridian-server/extension/         — Chrome extension v1.3
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

---

## Intelligence Brief Pipeline (Session 31 — FULLY WORKING ✅)

### Overview
- brief_pdf.py — standalone module, ReportLab + Pillow, generates A4 PDF
- Single Sonnet call: text generated once, used for both modal display and PDF build
- Full brief includes Economist charts (subtopic sections only); short brief is text only
- Pillow + numpy installed: Mac + VPS venv

### User flow
1. Click "Short Brief" or "Full Intelligence Brief" on any theme
2. Modal opens with progress spinner — rotating step labels + elapsed seconds
3. ~60-90s later text brief renders in modal (Executive Summary in amber panel)
4. "⇓ Open as PDF" button (amber background, bold white text) top-right opens PDF in new tab
5. PDF built from same text (no second Sonnet call), charts embedded, text justified

### Single-call architecture
- Frontend polls /api/kt/brief for text; once done, passes text to /api/kt/brief/pdf
- PDF job receives pregenerated_text, skips Sonnet call, builds PDF directly
- Modal and PDF always show identical content
- window._pdfJobId stores the PDF job ID (set async after PDF job starts)
- Button reads window._pdfJobId at click time (not at render time — was a null race bug, fixed)

### Prompt design (_build_prompt in brief_pdf.py)
- Fully domain-agnostic — works across all 10 themes
- Statistics instruction: one or two concrete figures per section, never invented
- Section instruction: lead with finding, support with figures, close with implication
- Explicitly bans title heading and overview section
- No Source Notes section

### Article context (_build_article_context in brief_pdf.py)
- SOURCE + TITLE + SUMMARY + first 400 chars of EXCERPT per article
- Max 60 articles for full brief, 30 for short

---

## Chart Image Processing (_crop_economist_chart in brief_pdf.py)

### Image type detection
- Maps: caption contains "map:" — no top crop, no background whitening, bottom crop only
- Charts: caption contains "chart:" — full processing pipeline
- Double images: two stacked figures (Kharg Island etc.) — bottom crop only, no whitening

### Top crop algorithm (_find_top_crop)
- Scans y=6 to min(120, h//4) — the Economist title block never exceeds ~120px
- Uses brightness threshold 155 (not 130) to catch medium-grey italic subtitle text
- Crops at last_dark_y + 2 (the row immediately after the last title/subtitle text row)
- If last dark row is past y=95, falls back to scanning only y=6..95 — avoids cutting
  into colour legends that sit above the chart area (e.g. stacked bar chart legends)
- Maps bypass this function entirely

### Bottom crop algorithm (_find_bottom_crop)
- Scans top-to-bottom in lower 60% for first sustained near-white band
- Charts: requires 5+ consecutive near-white rows (threshold: >85% of pixels > 230)
- Maps: requires 8+ consecutive near-white rows (prevents legend box from triggering)
- Removes "CHART/MAP: THE ECONOMIST" footer + white separator
- Preserves: x-axis labels, tick marks, "Source: ..." text (all on beige, not white)

### Background whitening (_whiten_background)
- Replaces Economist beige (236, 235, 223) ± 18 tolerance with pure white
- Uses numpy vectorised operation — fast for 14 charts per brief
- Charts only; maps keep original colours

### Known edge cases (not yet solved)
- Inverted x-axis: a small number of Economist charts put axis labels at top, not bottom.
  The bottom crop may cut off these labels. Not reliably detectable without OCR.
  The 5-row white threshold reduces (but doesn't eliminate) this risk.
- Colour legends above chart area: the y=95 fallback handles most cases but very tall
  legends could still be clipped. Monitor and tune TITLE_REGION_END if needed.

### Figure captions and titles
- Caption sits ABOVE each image (rendered as caption row first, then image row)
- Format: "Figure N — [title]" in italic grey 8pt
- Consecutive Figure 1, 2, 3… numbering across full brief in reading order
- Title extracted from Haiku description: strips "The chart shows/compares/depicts..." openers,
  strips interpretive trailing verbs (surged, risen, fell, declined...),
  splits on comma/semicolon (not period — avoids breaking "U.S." abbreviations)
- Figure number is tracked in fig_counter[0] list (mutable closure)

### PDF layout
- Maps: rendered at full page width (pw ≈ 16.6cm), each on its own row, max height 10cm
- Charts: rendered as pairs (2 per row) at half page width (cw ≈ 8.0cm), max height 7cm
- Pair height normalised: both images in a pair scaled to the shorter one's height
- is_map flag passed through process_chart() dict so layout code can branch correctly

### Chart selection rules
- No charts in: Executive Summary, Overview, Cross-cutting Themes, Strategic Implications,
  Watch List, Key Developments, Source Notes
- Cross-brief similarity dedup: >50% description token overlap → rejected
- Solo charts (only 1 qualifies for a section) → 0 charts shown (never unpaired)
- Budget: up to 2 per section, global cap 14 charts per brief

---

## Flask Routes — Brief Pipeline
- POST /api/kt/brief             — text brief (async), returns {ok, job_id}
- GET  /api/kt/brief/status/<id> — poll {status, brief, error}
- POST /api/kt/brief/pdf         — PDF job (async), accepts optional {text} pregenerated_text
- GET  /api/kt/brief/pdf/status/<id>   — poll {status, ready, size, error}
- GET  /api/kt/brief/pdf/download/<id> — serve completed PDF

---

## Economist Chart & Map Capture (Session 26 ✅)

### article_images DB schema
```sql
CREATE TABLE IF NOT EXISTS article_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id TEXT NOT NULL,
    caption TEXT NOT NULL,         -- "chart: the economist" or "map: the economist"
    description TEXT DEFAULT '',   -- visual description, 25 words, Haiku
    insight TEXT DEFAULT '',       -- analytical point, 30 words, enriched separately
    image_data BLOB NOT NULL,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    captured_at INTEGER NOT NULL,
    mac_id INTEGER DEFAULT NULL    -- Mac autoincrement PK, used for VPS dedup
)
```

### DB state (1 April 2026)
- Mac: 153 images, 153 with insight
- VPS: 153 images (87 legacy rows deleted Session 29)

### Image sync to VPS
- POST /api/push-images — receives images from Mac, upserts on mac_id
- wake_and_sync.sh pushes images on every sync

---

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

### Key patterns
- Write brief_pdf.py via filesystem:write_file (never heredoc — corrupts regex)
- Patch scripts: use filesystem:write_file + python3 ~/meridian-server/tmp_patch.py
- VPS Python: write script → deploy.sh (never inline -c strings with nested quotes)
- After deploy: nginx no-cache means hard refresh always gets latest
- JS regex corruption: patch scripts must not embed literal \n inside regex literals
- Shell endpoint filters keywords: base64-encode output or write to /tmp/ if needed

### Dangerous operations checklist
Before any DELETE/UPDATE: SELECT preview first, state what will be affected, then execute.
Lesson: Session 19 deleted all user bookmarks assuming they were junk.

---

## Service Worker
- sw.js cache version: meridian-v5
- nginx: no-cache for meridian.html and sw.js
- If stuck: DevTools → Application → Service Workers → Unregister → hard refresh

## Schedule (Geneva/CEST)
- 05:40 / 11:40 — Mac syncs FT + Economist + FA via Playwright
- 05:50 / 11:50 — VPS scores, agent auto-saves 8+ to Feed
- 23:00 — DB backup to VPS (7 days retained)

---

## Next Steps (priority order)
1. **Clean up tmp_ files** — many tmp_*.py, tmp_*.png committed during Sessions 28-31
   (run: git rm tmp_*.py tmp_*.png *.png and recommit)
2. **Chart-to-brief integration review** — chart selection scoring works well; consider
   whether score threshold (_MIN_SCORE=2) is right for non-Iran-war themes
3. **Foreign Affairs paywall** — FA articles still truncating at ~1,400 chars.
   Investigate: check fa_profile/ cookie freshness, try re-login via Playwright
4. **PWA icons** — proper 192×192 and 512×512
5. **Newsletter auto-sync** — newsletter_sync.py gitignored; VPS cannot auto-sync

---

## Build History

### 1 April 2026 (Session 31)
**Intelligence Brief PDF — image processing and layout overhaul (many commits)**

Chart cropping (commits d0ad6097 → a2f87d36):
- Top crop: scans y=6..120, threshold 155 (catches grey italic subtitle text)
  crops at last_dark_y+2; falls back to y=6..95 scan if dark rows extend past y=95
  (prevents cutting into colour legends above chart area)
- Bottom crop: 5-row white band for charts, 8-row for maps
  (prevents map legend boxes from triggering premature crop)
- Maps: no top crop, no whitening; rendered at full page width (not paired half-width)
- Maps: is_map flag propagated through process_chart() → PDF layout branching
- Double images: footer-only crop, no whitening

Figure title extraction:
- Strips "The chart shows/compares/depicts/presents/tracks..." openers
- Strips interpretive verbs (surged, risen, fell, declined, grown, soared, plunged...)
- Smart period splitting: only splits at sentence boundaries (capital letter following),
  not at abbreviations like "U.S." — eliminates "U — S" title bug
- Falls back to first two comma-clauses if title is too short/generic

pdfJobId null race condition (344c793c):
- window._pdfJobId stores job ID (set async); button reads at click time not render time

PDF button style: amber background, bold white, 2px border, rounded (9:18 patch)
Modal text: text-align: justify (9:18 patch)

### 1 April 2026 (Session 30)
- Single Sonnet call architecture: text generated once, passed to PDF job (d76300c2)
- Unified prompt _build_prompt(), richer context _build_article_context()
- Chart image processing: background whitening, bottom label crop, top title crop,
  Figure N captions, consecutive numbering (0c41c433, 41c8cf95)

### 1 April 2026 (Session 29)
- Brief modal: text preview + "Open as PDF ↗" replacing auto-download
- Progress ticker during generation (rotating steps + elapsed time)
- sw.js fixed (was empty on VPS), cache bumped to v5, nginx no-cache headers
- JS regex corruption fixed (literal newlines in patch scripts)

### 31 March 2026 (Session 28)
- brief_pdf.py rewritten from scratch, PDF pipeline end-to-end
- article_images sync Mac→VPS, mac_id dedup, 153 images pushed

### Earlier sessions (26-27)
- Economist chart capture, insight enrichment, KT themes, article grid

---

## GitHub Visibility
- Repo: PUBLIC — github.com/dakersalex/meridian-server
- Excluded: credentials.json, cookies.json, meridian.db, newsletter_sync.py, venv/

## Session Starter Prompt
---
You are helping me build Meridian, my personal news aggregator. Please read my technical notes from the Filesystem MCP at /Users/alexdakers/meridian-server/NOTES.md and review them. Then run the session start health check.
---

Note for Claude: Read NOTES.md via Filesystem MCP (NOT GitHub URL — blocked). Check Flask via shell endpoint before proceeding. Never restart Flask via the shell endpoint.
