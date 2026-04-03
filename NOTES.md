# Meridian — Technical Notes
Last updated: 3 April 2026 (Session 37 — brief improvements, FT enrichment, key facts UI)

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
- ~/meridian-server/backfill_progress.html — Chart backfill progress monitor page
- ~/Library/LaunchAgents/com.alexdakers.meridian.plist       — Auto-start Flask (Mac)
- ~/Library/LaunchAgents/com.alexdakers.meridian.http.plist  — Auto-start HTTP (Mac)
- ~/Library/LaunchAgents/com.alexdakers.meridian.sync.plist  — Auto-start sync (Mac)

## Mac Flask launchd (IMPORTANT)
- Python: /usr/bin/python3 (no venv — launchd plist runs server.py directly)
- To restart Flask safely: kill the PID on 4242 and launchd will respawn
  `lsof -ti tcp:4242 | xargs kill -9`
- NEVER rely on shell endpoint surviving a Flask kill — it dies with the process
- If two PIDs appear on 4242 (port conflict): kill both, launchd spawns one clean copy
- Symptom of stale process: server-error.log fills with "Port 4242 is in use"

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

## Database (3 April 2026 — VPS)
| Source | Total | Full text | Has summary | Avg body | Avg summary |
|---|---|---|---|---|---|
| The Economist | 268 | 262 (98%) | 262 (98%) | 6,033 chars | 453 chars |
| Financial Times | 173 | 169 (98%) | 172 (99%) | 4,350 chars | 388 chars |
| Foreign Affairs | 64 | 57 (89%) | 62 (97%) | 11,470 chars | 443 chars |
| Bloomberg | 38 | 37 (97%) | 36 (95%) | 5,659 chars | 369 chars |

Notes:
- FT: 29 articles had full_text but no summary — fixed Session 37 via VPS enrichment script
- FA: 7 articles without full_text are harder paywall tier — body not scrapable
- FA: 5 articles have summary but not full_text status — minor inconsistency, harmless
- Economist: 6 title_only articles — likely bookmarked but not yet scraped

---

## Autonomous Mode (Claude in Chrome + shell endpoint)

### CRITICAL: Claude must ALWAYS run commands autonomously
Claude has full access to run all terminal commands, patches, and deployments via:
- **Filesystem MCP** — write patch scripts to ~/meridian-server/
- **Shell bridge** — execute via window.shell() in Tab A (localhost)
- **deploy.sh** — commit, push and deploy to VPS in one command

**Claude must NEVER ask Alex to run Terminal commands.** This includes:
- Running patch scripts (filesystem:write_file → window.shell('python3 ~/meridian-server/tmp_*.py'))
- Syntax checks (window.shell('python3 -m py_compile ~/meridian-server/server.py'))
- Deploying (window.shell('cd ~/meridian-server && ./deploy.sh "message"'))
- SSH/VPS commands (write script locally → scp to VPS → ssh to run it)
- Checking logs (fetch via shell bridge → write to ~/meridian-server/logs/*.txt → read via Filesystem MCP)

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
- VPS operations: scp script to VPS → ssh to run it → tail result file
- Shell endpoint filters some keywords — write output to ~/meridian-server/logs/*.txt, read via Filesystem MCP
- Line-number patches are DANGEROUS — always use str.replace(OLD, NEW) with exact text
- Always python3 -m py_compile server.py before deploying
- After deploying, verify via live site tab (Tab B)
- Tmp files: always clean up after sessions
- ft_profile / economist_profile / fa_profile are used by launchd sync — never run Playwright
  against them while sync service is active (profile lock causes 0-char results)

### VPS Python scripts
- Always use venv: `source /opt/meridian-server/venv/bin/activate`
- enrich_article_with_ai() updates the art dict in-place but does NOT write to DB
  Must manually UPDATE articles SET summary=? after calling it
- /api/enrich/<aid> route — was broken (cx.description scoping bug), fixed Session 37

### Dangerous operations checklist
Before any DELETE/UPDATE on DB: SELECT preview first, confirm what will be affected, then execute.

---

## Article Body Text — Architecture (IMPORTANT)

### Correct architecture (enforced from Session 36)
- `body` = raw scraped article text from Playwright (5,000–20,000 chars for full articles)
- `summary` = 2-3 sentence AI summary (Haiku) — used for Feed card previews + keyword matching
- `status = 'full_text'` = body was successfully populated from Playwright

### The fullSummary overwrite bug — FIXED (Session 36)
- `enrich_article_with_ai` now only writes to `body` if currently empty (<200 chars)

---

## Source-Specific Notes

### Financial Times
- Scraper: Playwright, `ft_profile/`, saved articles page + article text fetch
- Selector (updated Session 36): `div.n-content-body p` (primary)
  fallback: `div[class*='n-content-body'] p`, `div[class*='article__content'] p`
- Session: expires periodically, requires manual re-login to ft_profile Chromium
- 29 articles enriched with summaries Session 37 (were full_text but missing summary)

### The Economist
- Scraper: Playwright, `economist_profile/`, bookmarks + homepage agent picks
- Selector: `p[data-component="paragraph"]` — confirmed working
- headless=False required (Cloudflare detection)

### Foreign Affairs
- Scraper: Playwright, `fa_profile/`, saved articles page
- TWO page templates: `div.article__body-content p` + `section.rich-text p`
- Session: Drupal cookie valid until 2026-05-23
- AI theme: FA correctly has minimal presence (~4 articles) — FA covers AI as geopolitics,
  not tech. Only "America Is Losing the Innovation Race" scores strongly on AI keywords.

### Bloomberg
- NO automated scraper — Bloomberg bot detection kills headless Playwright
- All articles added via Chrome Extension v1.3 clip button

---

## Feed Source Restriction
Only FT/Economist/FA/Bloomberg auto-saved to Feed. Others stay in Suggested.
`FEED_CORE_SOURCES = {'Financial Times', 'The Economist', 'Foreign Affairs', 'Bloomberg'}`

---

## Key Themes (KT) System

### Current state (3 April 2026)
- 8 themes on VPS, sorted by article count descending
- key_facts: ✅ 10 facts per theme across all 8 themes
- Theme article counts: Iran War 177, Financial Markets 146, Trump/US Politics 115,
  Energy Markets 61, AI Race 59, Demographics 57, Europe 52, US-China Trade 50

### Theme grid (Session 37)
- kt-fact-top: padding 2px 12px 6px, height 68px, flex-start, gap 1px, overflow hidden
- kt-fact-title: no margin-top (removed auto — was causing bottom-anchoring)
- All 10 key fact cards uniform height, number+title top-aligned

### kt/seed pipeline
- Call 1: Sonnet → 8 themes. Call 2: Haiku → article assignments. Call 3: Haiku → key_facts
- Article assignment is AI-based (Haiku), NOT a keyword threshold — results stored implicitly
- KT theme article counts are re-derived at query time from keyword scoring

---

## Intelligence Brief Pipeline

### Article selection (redesigned Session 37)
- **Old**: 4 equal-count buckets × 15 articles, source cap 5/bucket = max 60 articles to Sonnet
- **New** (`_build_article_context` in brief_pdf.py):
  - All candidates scored: `(full_text bonus + summary length) × recency multiplier`
  - Recency: ×1.5 last 7 days, ×1.2 last 30 days, ×1.0 older
  - Temporal anchor: 10% of n, min 3 max 10 — oldest-third articles guaranteed in
  - No source cap — proportional representation by quality
  - Cap: 150 articles max (irrelevant at current corpus sizes ≤59/theme)
  - Short and Full briefs use IDENTICAL article input — difference is output only
  - Same logic shared via `/api/brief/context` endpoint for bgGenerate modes

### Brief header (fixed Session 37)
- Now shows actual articles fed to Sonnet (selected_count), not full pool size
- Old header showed pool size (e.g. 53) even though Sonnet only saw 40
- `build_brief_pdf` signature: `selected_count=None` parameter added

### /api/enrich/<aid> route (fixed Session 37)
- Was broken: `cx.description` used outside `with` block → 500 error
- Fix: uses `cx.row_factory = sqlite3.Row` inside context, writes summary back explicitly

### bgGenerate (All themes / Focused topic)
- Now calls `/api/brief/context` server-side for article selection
- Shares same scoring/anchor logic as PDF pipeline
- Previously: naive `filteredArts.slice(0, maxArts)` with no scoring

### /api/brief/context endpoint (new Session 37)
- POST {articles, brief_type} → returns {context: str, count: int}
- Uses `_build_article_context` from brief_pdf.py

---

## Chart/Image System

- 163 images across 89 Economist articles — confirmed ceiling (Session 37 backfill)
- All 173 remaining articles processed: genuinely text-only, no chart figures
- Do not re-run backfill on existing articles

### Backfill progress page
- ~/meridian-server/backfill_progress.html → http://localhost:8080/backfill_progress.html
- /api/images/recent endpoint: returns last N images as base64 (sqlite3.connect pattern)

---

## Service Worker
- sw.js cache version: meridian-v5

## Schedule (Geneva/CEST)
- 05:40 / 11:40 — Mac syncs FT + Economist + FA via Playwright
- 05:50 / 11:50 — VPS scores, agent auto-saves to Feed

---

## Next Steps (priority order)

1. **Sort theme articles by relevance** — detail panel shows most recent first; sort by
   keyword hit count + recency.

2. **Sub-topics filtering** — filter chips do nothing; decide implement or remove.

3. **Checking server retry loop** — frontend shows "Checking server" during Flask restart
   (~8-10s). Add JS retry loop (every 3s, up to 30s) so deploy restarts are invisible.

4. **FA session renewal** — Drupal cookie expires 2026-05-23.

5. **Brief quality review** — compare brief #18 (old algo) vs #19 (new algo) on AI theme.
   Key improvement: 40→53 articles to Sonnet, no source cap, recency weighting.

6. **ft_profile lock** — safe window for manual FT Playwright: outside 05:35-06:00 / 11:35-12:00.

7. **Economist title_only (6 articles)** — likely bookmarked but not scraped. Will self-correct
   on next sync if articles are still accessible.

---

## Build History

### 3 April 2026 (Session 37 — brief improvements, enrichment, UI fixes)

**Key fact card UI fixes**
- Removed `margin-top: auto` from `.kt-fact-title` — was anchoring titles to bottom
- `.kt-fact-top`: padding 2px 12px 6px, height 68px fixed, justify-content flex-start, gap 1px
- All 10 cards uniform height, number+title top-aligned

**Chart backfill — exhausted**
- All 173 remaining Economist articles processed: 0 new images (genuinely text-only)
- 163 images / 89 articles is confirmed ceiling

**Brief article selection — complete redesign**
- Score-based with recency multiplier replacing equal-count bucket system
- No source cap, temporal anchor, shared logic for all brief types
- Short and Full briefs now use same articles — output length is the only difference
- bgGenerate now uses server-side /api/brief/context instead of naive slice

**Brief header fix**
- Shows actual articles fed to Sonnet, not full input pool
- Old: "53 articles" even when Sonnet only saw 40

**FT 29-article summary enrichment**
- 29 FT full_text articles had no summaries on VPS
- Enriched via VPS script using Haiku — all 29 saved ✅
- FT now 99% summary coverage

**/api/enrich/<aid> route fixed**
- cx.description scoping bug caused 500 errors
- Now uses sqlite3.Row, properly writes summary back to DB

**FA AI theme investigation**
- FA correctly has minimal AI theme presence (4 articles)
- FA covers AI as geopolitics/security, not technology
- Only "America Is Losing the Innovation Race" scores strongly on AI keywords

**New files/routes**
- /api/brief/context — shared article selection for all brief modes
- /api/images/recent — base64 image fetch for monitoring
- backfill_progress.html — chart backfill progress page

### 3 April 2026 (Session 36)
- enrich overwrite bug fixed, Economist + FA re-enrichment
- FT selector updated, Feed source restriction
- Briefing Generator JS SyntaxError fixed

### 2 April 2026 (Session 35)
- FA selector fix, KT crash fix, permanent/manual theme grid

### 1 April 2026 (Sessions 29-34)
- Brief PDF pipeline, KT system, chart processing

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
