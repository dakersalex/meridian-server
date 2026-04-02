# Meridian — Technical Notes
Last updated: 2 April 2026 (Session 35 — FA fix, Economist backfill, theme crash fix, tmp cleanup)

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
- ~/meridian-server/wake_and_sync.sh   — Mac sync + VPS push script (runs on wake)
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
View logs: cat /opt/meridian-server/meridian.log | tail -50

## Deploying Code Updates
One command from Mac (via shell bridge — Claude runs this autonomously):
  cd ~/meridian-server && ./deploy.sh "description"
(git add -A, commit, push, SSH pull on VPS, systemctl restart meridian)

## Database (2 April 2026)
- Mac: ~531 articles total. Economist: 258 full_text. FA: 52 total, 41 full_text (avg 7,930 chars).
- VPS: 495 full_text articles pushed from Mac (backfill complete). Economist gap resolved.

---

## Autonomous Mode (Claude in Chrome + shell endpoint)

### CRITICAL: Claude must ALWAYS run commands autonomously
Claude has full access to run all terminal commands, patches, and deployments via:
- **Filesystem MCP** — write patch scripts to ~/meridian-server/
- **Shell bridge** — execute via window.shell() in Tab A (localhost)
- **deploy.sh** — commit, push and deploy to VPS in one command

**Claude must NEVER ask Alex to run commands in Terminal.** This includes:
- Running patch scripts (filesystem:write_file → window.shell('python3 ~/meridian-server/tmp_*.py'))
- Syntax checks (window.shell('python3 -m py_compile ~/meridian-server/server.py'))
- Deploying (window.shell('cd ~/meridian-server && ./deploy.sh "message"'))
- SSH/VPS commands (write script → scp to VPS → ssh to run it)
- Checking logs (fetch via shell bridge → write to ~/meridian-server/tmp_*.txt → read via Filesystem MCP)

Alex is not present during execution. Complete all tasks end-to-end autonomously.

### Shell bridge (re-inject at start of each JS block)
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

### NEVER restart Flask via shell endpoint — kills itself mid-request

### Key patterns
- Write patch scripts via filesystem:write_file → execute via window.shell()
- VPS operations: write script locally → scp to VPS → ssh to run it
- Shell endpoint filters some keywords — write output to ~/meridian-server/tmp_*.txt, read via Filesystem MCP
- Line-number patches are DANGEROUS — always use str.replace(OLD, NEW) with exact text
- Always python3 -m py_compile server.py before deploying
- After deploying, verify via live site tab (Tab B)
- Tmp files: always clean up with git rm tmp_*.py tmp_*.txt after sessions

### Dangerous operations checklist
Before any DELETE/UPDATE on DB: SELECT preview first, confirm what will be affected, then execute.

---

## Key Themes (KT) System

### Current state (2 April 2026)
- **8 themes** on VPS, sorted by article count descending
- key_facts: ⚠️ still 0 on all themes (max_tokens fix deployed but seed ran before it)
  → Trigger one more Reset Themes on live site at start of next session
- 531 articles tagged

### kt_themes dedup bug — FIXED
- `kt_themes` uses `name` as PRIMARY KEY — re-seeds with slightly different names accumulate rows
- Fixed: `/api/kt/themes` now filters by `MAX(last_updated)` so only latest seed is returned
- If accumulation ever happens again: delete stale rows on VPS by timestamp (keep latest batch)

### Theme grid design (Session 35)
- **8 AI-generated themes** sorted by matched article count (most articles top-left)
- **2 manual slots** (silver dashed border) — modal with name + keywords + emoji
  - Stored in localStorage: `meridian_manual_themes`
  - Auto-marked permanent on creation
- **★ Permanent themes** (gold border + "PERMANENT" badge)
  - Click ☆ star to make permanent; stored in localStorage: `meridian_permanent_themes`
  - Survive Reset Themes — listed in confirm dialog
  - Un-star before reset to allow free regeneration
- **Reset Themes confirm** lists permanent themes by name

### kt/seed pipeline (3-call architecture)
- **Call 1** — Sonnet: 165 representative titles → 8 themes. max_tokens=3000, timeout=60s
- **Call 2** — Haiku: batches of 50 → article→theme assignments
- **Call 3** — Haiku per theme → key_facts + subtopic_details. max_tokens=2500, timeout=45s

### Seeding prompt (Call 1)
- Requests exactly 8 themes
- Consolidation rules: never split same geographic theatre or tech race
- Bans generic keywords: war, military, conflict, economy, geopolitics, policy, crisis

---

## Intelligence Brief Pipeline (✅ WORKING)

### Overview
- brief_pdf.py — ReportLab + Pillow, generates A4 PDF
- Single Sonnet call: text used for both modal display and PDF build
- Full brief includes Economist charts; short brief is text only

### Article context
- Temporal bucketing: 4 buckets × 15 articles = up to 60 (full brief)
- full_text articles first, then by summary length; per-source cap 5 per bucket

### Chart selection rules
- No charts in: Executive Summary, Overview, Cross-cutting Themes, Strategic Implications etc.
- Cross-brief similarity dedup: >50% token overlap → rejected
- Solo charts → 0 shown; budget: up to 2 per section, global cap 14 per brief

---

## Foreign Affairs — FIXED (Session 35)

### Root cause
- `fetch_fa_article_text` used wrong CSS selector (`div.article-body p`)
- Correct selector (confirmed via Playwright April 2026): `div.article__body-content p`
- Old selector returned no text → body stored as AI-generated fullSummary (~2,500 chars)

### Fix applied
- Selector updated in server.py: `div.article__body-content p` (primary)
  then `div.article__body p`, `div.article-body p`, `main p` as fallbacks
- Re-enrichment ran: 41/51 FA articles now have raw text (avg 7,930 chars, was 2,500)
- 10 articles skipped — genuinely paywalled at a stricter tier (no text returned by selector)

### FA session status
- Session IS authenticated (has_my_account=True in page content)
- Drupal session cookie `SSESS8d72...` valid until 2026-05-23
- No re-login needed currently

---

## Economist — FIXED (Session 35)

### Root cause of VPS gap (14 full_text vs 258 on Mac)
- `wake_and_sync.sh` push script used a 3-hour lookback window
- Older personal bookmarks enriched >3hrs ago were never pushed

### Fix applied
- `wake_and_sync.sh` now pushes ALL `full_text` articles on every sync (no time window)
- Batches of 50 with 0.3s sleep — safe to run every sync, VPS skips richer existing records
- One-time backfill push: 495 articles → VPS (was 14 Economist full_text)

---

## Economist Chart & Map Capture (Session 26 ✅)
- Mac: 156 images, 86 articles with images
- VPS: synced via push-images on each wake_and_sync.sh run

---

## Service Worker
- sw.js cache version: meridian-v5
- nginx: no-cache for meridian.html and sw.js

## Schedule (Geneva/CEST)
- 05:40 / 11:40 — Mac syncs FT + Economist + FA via Playwright
- 05:50 / 11:50 — VPS scores, agent auto-saves 8+ to Feed

---

## Next Steps (priority order)
1. **Trigger Reset Themes on live site** — key_facts still blank (fix deployed, needs one more seed)
2. **AI theme split persists** — "AI Race US China Tech" is broadly correct but watch for further
   splitting on next seed. Add to consolidation rules if needed.
3. **Sort theme articles by relevance** — theme detail panel shows most recent first; sort by
   keyword hit count + summary length so most substantive articles surface first.
4. **Sub-topics filtering** — chips in theme panel clickable but do nothing; decide: implement
   filtering or remove and use subtopics only as brief section headings.
5. **Focused Intelligence Briefing** — free-text input for ad-hoc topic briefs.
6. **FA paywalled articles (10 remaining)** — investigate whether these are a different FA tier
   or need a different selector. Could try waiting longer after page load or scrolling to trigger
   content rendering.

---

## Build History

### 2 April 2026 (Session 35 — FA fix, backfill, theme crash fix)

**FA selector fix**
- Wrong selector `div.article-body p` → correct `div.article__body-content p`
- 41/51 FA articles re-enriched with raw text (avg 7,930 chars, was 2,500)
- FA session confirmed authenticated via Playwright inspection

**Economist VPS backfill**
- wake_and_sync.sh push window removed — now pushes all full_text every sync
- 495 articles pushed to VPS in one-time backfill

**Key Themes crash fix**
- JS crash: `Cannot read properties of undefined (reading 'keywords')`
- Root cause: two seed runs accumulated 16 rows in kt_themes (name-as-PK doesn't dedup)
- Fix 1: `/api/kt/themes` now filters by MAX(last_updated)
- Fix 2: null guard in renderThemeGrid filters themes missing name/keywords
- Stale 8 rows deleted directly from VPS DB

**Permanent/manual theme grid**
- 8 AI themes sorted by article count descending
- ☆/★ star button on each card for permanent status (gold border)
- 2 silver dashed manual slots with modal editor
- Both survive Reset Themes via localStorage

**Tmp file cleanup**
- All tmp_*.py, tmp_*.txt files removed from repo

**Commits this session**
- fix: kt/themes returns only latest seed; null guard in renderThemeGrid
- fix: FA selector article__body-content; wake_and_sync push all full_text
- feat: permanent/manual theme grid, sorted by article count, gold/silver cards
- docs: session 35 notes — autonomous execution rule, permanent/manual themes
- chore: remove all tmp_ files; FA re-enrichment complete

### 1 April 2026 (Session 34)
- getThemeArticles() tighter keyword matching
- kt/seed 3-call architecture with Haiku per-theme key_facts
- VPS SyntaxError recovery

### 1 April 2026 (Sessions 29-31)
- Intelligence brief PDF pipeline
- Chart image processing and PDF layout

### Earlier sessions (26-28)
- Economist chart capture, insight enrichment, article_images sync Mac→VPS

---

## GitHub Visibility
- Repo: PUBLIC — github.com/dakersalex/meridian-server
- Excluded: credentials.json, cookies.json, meridian.db, newsletter_sync.py, venv/

## Session Starter Prompt
---
You are helping me build Meridian, my personal news aggregator. Please read my technical notes from the Filesystem MCP at /Users/alexdakers/meridian-server/NOTES.md and review them. Then run the session start health check.
---

Note for Claude: Read NOTES.md via Filesystem MCP (NOT GitHub URL — blocked).
NEVER ask Alex to run Terminal commands — run everything autonomously via shell bridge.
Never restart Flask via the shell endpoint.
