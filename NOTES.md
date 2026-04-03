# Meridian — Technical Notes
Last updated: 3 April 2026 (Session 38 — 2D nav redesign, sync pipeline, source panel fixes)

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
| Source | Total | Full text | Has summary |
|---|---|---|---|
| The Economist | 269 | 263 | ~263 |
| Financial Times | 176 | 171 | ~172 |
| Foreign Affairs | 66 | 57 | ~62 |
| Bloomberg | 38 | 37 | ~36 |
| Other | 41 | — | — |
| **Total** | **590** | **538** | — |

Notes:
- VPS total: 590 articles, 538 full text (as of session 38)
- Mac DB: 560 articles (VPS agent generates its own auto-saves not pushed back to Mac)
- Newsletters: 60 on both Mac and VPS (synced session 38)

---

## Sync Architecture (IMPORTANT)

### Mac → VPS (wake_and_sync.sh)
1. Trigger Playwright scrapers (FT, Economist, FA)
2. Wait 90s for completion
3. Trigger AI enrichment of title-only articles
4. Trigger newsletter IMAP sync from iCloud
5. Push full_text articles to VPS via /api/push-articles
6. Push chart images to VPS via /api/push-images
7. Push newsletters to VPS via /api/push-newsletters
8. Push interviews to VPS via /api/push-interviews

### VPS-only data (never pushed to Mac)
- suggested_articles — VPS agent generates and saves high-scoring articles
- kt_themes — seeded on VPS via Haiku/Sonnet
- article_theme_tags — VPS assigns during KT seeding
- agent_log — VPS scoring records

### Mac-only data
- Local meridian.db (560 articles) — source of truth for ingestion
- Playwright browser profiles (ft_profile/, economist_profile/, fa_profile/)
- Chrome Extension clips (synced to Mac Flask, then pushed to VPS)

---

## Autonomous Mode (Claude in Chrome + shell endpoint)

### CRITICAL: Claude must ALWAYS run commands autonomously
Claude has full access to run all terminal commands, patches, and deployments via:
- **Filesystem MCP** — write patch scripts to ~/meridian-server/
- **Shell bridge** — execute via window.shell() in Tab A (localhost)
- **deploy.sh** — commit, push and deploy to VPS in one command

**Claude must NEVER ask Alex to run Terminal commands.**

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
- Shell endpoint filters some keywords — write output to ~/meridian-server/logs/*.txt
- Line-number patches are DANGEROUS — always use str.replace(OLD, NEW) with exact text
- Always python3 -m py_compile server.py before deploying
- After deploying, verify via live site tab (Tab B)
- Tmp files: always clean up after sessions

### VPS Python scripts
- Always use venv: `source /opt/meridian-server/venv/bin/activate`
- enrich_article_with_ai() updates the art dict in-place but does NOT write to DB
- /api/enrich/<aid> route — fixed session 37 (cx.description scoping bug)

### Dangerous operations checklist
Before any DELETE/UPDATE on DB: SELECT preview first, confirm, then execute.

---

## Article Body Text — Architecture

### Correct architecture
- `body` = raw scraped article text (5,000–20,000 chars for full articles)
- `summary` = 2-3 sentence AI summary (Haiku) — used for Feed previews + keyword matching
- `status = 'full_text'` = body successfully populated from Playwright

---

## UI Design (Session 38)

### 2D Navigation (dot + background)
- `#folder-switcher`: Meridian logo | News Feed · Key Themes · Briefing Generator | server status + AI Analysis
- Active tab: `background: var(--paper-2)` tray + amber dot (`.nav-dot` turns `var(--accent)`)
- Inactive tabs: muted text + gray dot, hover shows background tray
- `switchMode()`: removes `.active` from all tabs, adds to the selected one
- Info strip, sub-nav, feed header hidden when switching to Themes or Briefing

### Info strip (merged tally + activity)
- `#info-strip`: My saves n (n%) | AI picks n (n%) | 24h: [source pills] | Sync all | Clip Bloomberg
- Activity pills: `.activity-pill-active` (amber tint) when n>0, `.activity-pill-zero` (neutral) when 0
- `flex-wrap: nowrap` — always one line at full browser width

### Article card distinction
- AI picks: `✦ AI pick` amber filled badge + `.ai-pick` class → `border-left: 3px solid var(--accent)`
- My saves: `My save` neutral pill (paper-3 bg, rule border), no left border accent
- Class applied inline in renderFeed() template strings

### Sources panel
- Top 6 sources listed individually + `Other: n` row for remainder
- Total row = `articles.length` (all articles, not just shown sources)

---

## Source-Specific Notes

### Financial Times
- Scraper: Playwright, `ft_profile/`, saved articles page + article text fetch
- Session: expires periodically, requires manual re-login to ft_profile Chromium

### The Economist
- Scraper: Playwright, `economist_profile/`, bookmarks + homepage agent picks
- headless=False required (Cloudflare detection)

### Foreign Affairs
- Scraper: Playwright, `fa_profile/`, saved articles page
- Session: Drupal cookie valid until 2026-05-23

### Bloomberg
- NO automated scraper — Bloomberg bot detection kills headless Playwright
- All articles added via Chrome Extension v1.3 clip button
- Option in source filter dropdown added session 38

---

## Feed Source Restriction
Only FT/Economist/FA/Bloomberg auto-saved to Feed. Others stay in Suggested.
`FEED_CORE_SOURCES = {'Financial Times', 'The Economist', 'Foreign Affairs', 'Bloomberg'}`

---

## Key Themes (KT) System

### Current state (3 April 2026)
- 8 themes on VPS, sorted by article count descending
- key_facts: 10 facts per theme across all 8 themes ✅

### kt/seed pipeline
- Call 1: Sonnet → 8 themes. Call 2: Haiku → article assignments. Call 3: Haiku → key_facts

---

## Intelligence Brief Pipeline

### Article selection (redesigned Session 37)
- Score: `(full_text bonus + summary length) × recency multiplier`
- Recency: ×1.5 last 7 days, ×1.2 last 30 days, ×1.0 older
- Temporal anchor: 10% of n, min 3 max 10 — oldest-third articles guaranteed
- No source cap — proportional representation
- Short and Full briefs use identical article input

---

## Chart/Image System
- 163 images across 89 Economist articles — confirmed ceiling (session 37 backfill)
- Do not re-run backfill on existing articles

---

## Schedule (Geneva/CEST)
- 05:40 / 11:40 — Mac syncs FT + Economist + FA via Playwright
- 05:50 / 11:50 — VPS scores, agent auto-saves to Feed

---

## Next Steps (priority order)

1. **Sort theme articles by relevance** — detail panel shows most recent first; sort by
   keyword hit count + recency.

2. **Sub-topics filtering** — filter chips do nothing; decide implement or remove.

3. **Checking server retry loop** — frontend shows "Checking server" during Flask restart.
   Add JS retry loop (every 3s, up to 30s).

4. **FA session renewal** — Drupal cookie expires 2026-05-23.

5. **Points of Return gap** — latest newsletter is 2 Apr; check if forwarding rule lapsed
   or Bloomberg changed sender. Trigger manual sync to investigate.

6. **NOTES.md** — updated end of session 38.

---

## Build History

### 3 April 2026 (Session 38 — UI redesign, sync pipeline, source panel)

**2D nav design**
- Replaced folder-tab CSS with dot+background pattern
- `#folder-switcher` now contains logo + nav items + server status + AI Analysis
- Active tab: amber dot + background tray; inactive: gray dot + muted text
- `switchMode()` refactored to use `.active` class uniformly

**Info strip**
- Merged tally-bar + activity-bar into single `#info-strip`
- Activity pills: amber when source has new articles, neutral gray when zero
- Sync all + Clip Bloomberg always on right, never wraps

**Article card distinction**
- `✦ AI pick` amber badge + amber left border for auto-saved articles
- `My save` neutral pill for manually clipped articles

**Sources panel**
- Top 6 + Other row; Total = articles.length (590), consistent with tally

**Tally bar**
- Percentages shown: My saves 482 (82%) · AI picks 108 (18%)

**Newsletter + interview sync**
- `wake_and_sync.sh` now pushes newsletters and interviews to VPS after every sync
- `/api/push-newsletters` and `/api/push-interviews` endpoints added
- Backfilled 50 missing newsletters to VPS (10 → 60)

**Bloomberg source filter**
- Added to source filter dropdown (was missing)

### 3 April 2026 (Session 37 — brief improvements, FT enrichment, key facts UI)
- Brief article selection redesigned (score-based, recency multiplier, temporal anchor)
- FT 29-article enrichment — all enriched via VPS Haiku calls
- /api/enrich/<aid> fixed (cx.description scoping bug)
- Chart backfill exhausted — 163/89 is confirmed ceiling

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
