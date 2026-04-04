# Meridian — Technical Notes
Last updated: 4 April 2026 (Session 41 — stats panel redesign, pub_date normalisation, HTML dedup)

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

## Mac Flask launchd (IMPORTANT)
- Python: /usr/bin/python3 (no venv — launchd plist runs server.py directly)
- To restart Flask safely: kill the PID on 4242 and launchd will respawn
  `lsof -ti tcp:4242 | xargs kill -9`
- NEVER rely on shell endpoint surviving a Flask kill — it dies with the process

## Daily Use
Open in browser (any device, any network):
https://meridianreader.com/meridian.html

Mac local (if needed):
http://localhost:8080/meridian.html

## VPS Management
SSH in: ssh root@204.168.179.158
Check Flask: systemctl status meridian
Restart Flask: systemctl restart meridian
View logs: cat /opt/meridian-server/meridian.log | tail -50

## Deploying Code Updates
  cd ~/meridian-server && ./deploy.sh "description"
(git add -A, commit, push, SSH pull on VPS, systemctl restart meridian)

## Database (4 April 2026 — VPS)
| Source | Total | Full text |
|---|---|---|
| The Economist | 272 | ~265 |
| Financial Times | 181 | ~179 |
| Foreign Affairs | 66 | 57 |
| Bloomberg | 38 | 37 |
| Other | ~19 | — |
| **Total** | **~596** | **~541** |

---

## pub_date Format (normalised Session 41)
All pub_dates stored as ISO `YYYY-MM-DD` in both Mac and VPS databases.
`normalize_pub_date()` in server.py handles all incoming formats:
- `DD Month YYYY` → e.g. `01 April 2026` → `2026-04-01`
- `Month D, YYYY` → e.g. `April 2, 2026` → `2026-04-02`
- `Month YYYY` (no day) → e.g. `March 2026` → `2026-03-01` (1st of month)
- Relative (`X days ago`, `yesterday`, `today`) → resolved to absolute ISO date
- ISO passthrough → unchanged

Called in `upsert_article()` so every write is clean.
Enrichment prompt instructs Haiku to return `YYYY-MM-DD` format.
One-off migration: Mac (24 fixed), VPS (41 fixed).

Typical cadence: FT 3–6/day, Economist 2–8/day (edition drops Tue/Thu/Sat), FA 1–2/day.

---

## Sync Architecture
### Mac → VPS (wake_and_sync.sh)
1. Playwright scrapers (FT, Economist, FA)
2. AI enrichment of title-only articles
3. Newsletter IMAP sync from iCloud
4. Push articles → /api/push-articles
5. Push images → /api/push-images
6. Push newsletters → /api/push-newsletters
7. Push interviews → /api/push-interviews

---

## Autonomous Mode
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
- Tab A (localhost:8080/meridian.html): shell bridge
- Tab B (meridianreader.com/meridian.html): live site verification
- TabIds change every session — always call tabs_context_mcp first

### Key patterns
- Write patch scripts via filesystem:write_file → execute via window.shell()
- Line-number patches are DANGEROUS — always use exact text str.replace()
- For large deletions, line-index slicing in Python (lines[:N] + lines[M:]) is safe when anchors are verified first
- Syntax check for HTML/JS files: extract script blocks and check, not ast.parse (that's Python-only)
- Correct pre-deploy check: grep for key IDs, check HTML_LANG_COUNT=1, check DOCTYPE=1
- After deploying, verify via live site tab (Tab B)
- Check for duplicate `<html>` tags: `grep -c "<html lang" meridian.html` should return 1

### CRITICAL: Duplicate HTML bug prevention
After any patch replacing a large HTML block, always verify:
  grep -n "<!DOCTYPE\|<html lang" ~/meridian-server/meridian.html
Expected: line 1 only (plus any inside JS template strings). Never deploy if there are two `<html lang` tags.

### tmp_ files
- tmp_*.py, tmp_*.txt, *.bak* are all gitignored
- Write scripts to ~/meridian-server/tmp_*.py, read output from tmp_*.txt
- Clean up at end of session: rm -f tmp_*.txt tmp_*.py

### Shell output keyword filter
The shell bridge swallows output containing certain words ("api", "fetch", "query string", etc.).
Workaround: write results to tmp_*.txt and read via Filesystem MCP.

---

## UI Design — Current State (Session 41)

### Colour Palette (Palette 1A)
```css
--paper: #faf8f4          /* content zone: cards, sidebar, feed area */
--paper-2: #f0ece3        /* header rows: masthead, nav, sub-nav, filter */
--paper-3: #e4dfd4        /* badges, neutral elements */
--accent: #c4783a         /* logo "dian", AI Analysis button, card hover border */
--ink: #1a1a1a            /* active tab underline, active badge, headings */
--green: #2d6b45          /* full text badge, live activity pills */
--rule: rgba(0,0,0,0.1)  /* dividers */
```

### Source colours (used in stats panel)
```
Financial Times:  #1e4d8c  (blue)
The Economist:    #8b1a1a  (dark red)
Foreign Affairs:  #2a7a5a  (teal-green — distinct from FT blue)
Bloomberg:        #555     (charcoal)
Other:            #999
```

### Row structure (sticky, stacked)
```
Row 1: Masthead — logo + tagline | date + synced time + green/red dot + connected
Row 2: Folder-switcher — News Feed · Key Themes · Briefing Generator | Sync all · AI Analysis
Row 3: Main-nav — FEED · ARCHIVE · NEWSLETTERS · INTERVIEWS · SUGGESTED
Row 4: Filter — All articles · All curation · All sources · Last 6 months | 📊 Stats · 📎 Clip Bloomberg
Row 5: Info-strip (Stats panel, hidden by default, toggled by Stats button — NOT sticky, pushes content down)
```

### Sticky top values (px, from recalcStickyTops())
- Masthead: top 0 (h≈68)
- Folder-switcher: top 67 (h≈44)
- Main-nav: top 111 (h≈35)
- Filter row: top 146 (h≈41)
- Info-strip: **position:relative** (NOT sticky) — expands in normal flow, pushes feed down
- recalcStickyTops() must NOT set top on #info-strip

### Stats panel (#info-strip) — redesigned Session 41
Background: `#fff` (white), bottom border: `2px solid #e0dbd0`
Toggled by 📊 Stats button in filter row. Rendered by `renderNewStats()` (IIFE called in loadAll).

**Row 1** — 3 equal columns (`grid-template-columns: 1fr 1fr 1fr`, `align-items: stretch`):
- **Col 1**: Headline numbers (Total / My saves / AI picks / Full text, 26px bold) + Curation split over time (3 bars: All time / 30 days / 7 days, 14px tall, % inside bars, label inline left at 44px)
- **Col 2**: New articles ingestion table — rows: FT / Economist / FA / Bloomberg / Other / Total; columns: 24h / 48h / 7d / 14d
- **Col 3**: 14-day ingestion sparkline — stacked bars per day coloured by source; x-axis shows day name (Mon/Tue…) + date (d/m) in two rows, weekends bolder; SVG uses `flex:1` to fill column height equally

All three cols use `display:flex;flex-direction:column` — sparkline SVG has `flex:1` so it expands to match the tallest column. Verified equal height (177px) before deploy.

**Row 2** — 3 equal columns:
- By source (horizontal bars, source colours)
- Full text coverage (green bars, % values coloured green/amber)
- By topic (top 5, dark red bars)

**Row 3** — 4 columns, Option C style (bottom-rule header `border-bottom:1px solid #1a1a1a`, no card box):
- ⏱ Last scraped — days since most recent article per source (green ≤1d, amber ≤7d, red >7d)
- 📋 Unenriched backlog — title-only count per source (green=clean, amber≤5, orange>5)
- 📈 7-day rate — article count + per-day average, colour-coded
- ✦ Agent activity — auto-saved total / last 7 days / rate this week / all-time rate

**DOM IDs for renderNewStats()**: sp-total, sp-saves, sp-ai, sp-ft, sp-cur-bars, sp-ingest-table, sp-sparkline, sp-spark-legend, sp-src-bars, sp-cov-bars, sp-topic-bars, sp-last-scraped, sp-backlog, sp-rate, sp-agent

Legacy hidden IDs preserved for JS compatibility: stat-total, stat-saves, stat-ai, stat-ft, stat-24h-top, stat-src-bars, stat-cov-bars, stat-topics, act-ft/eco/fa/bbg/fp and pill variants, tally-* etc.

### Article card layout (Option 3 — fixed date column)
```
[date col 44px] [card-body flex:1]
                [card-header: source · topic | ✕ delete btn]
                [article-title (Playfair serif)]
                [article-summary]
                [card-footer: Full text badge · AI pick/My save · tags]
```

### Server status
- ONE instance only: in masthead right, below date
- Format: `Synced 10:08 • meridianreader.com · connected`
- Green dot when connected, red when error

---

## Source-Specific Notes

### Financial Times
- Scraper: Playwright, `ft_profile/`
- Session expires periodically — manual re-login needed
- Typical cadence: 3–6 articles/day

### The Economist
- Scraper: Playwright, `economist_profile/`
- headless=False required (Cloudflare detection)
- Edition drops Tue/Thu/Sat — expect 5–10 articles on those days, 1–3 otherwise

### Foreign Affairs
- Scraper: Playwright, `fa_profile/`
- Session: Drupal cookie valid until **2026-05-23**

### Bloomberg
- No automated scraper — Chrome Extension v1.3 only

---

## Key Themes (KT) System
- 8 themes on VPS, sorted by article count descending
- 3-call architecture: Sonnet (theme gen) → Haiku (assignment) → Haiku (key_facts)
- KT lives on VPS only — Mac local DB has kt_themes table but it is always empty

### Current themes (4 April 2026 — VPS)
| Theme | Articles |
|---|---|
| Iran War and Middle East | 185 |
| Financial Markets and Investors | 148 |
| Trump Administration and US Politics | 117 |
| Energy Markets and Oil Shock | 62 |
| AI Race and Tech Industry | 59 |
| Demographics, Society and Culture | 57 |
| Europe's Strategic Repositioning | 53 |
| US-China Trade and Tech War | 51 |

---

## Outstanding Issues / Next Steps

1. **Sort theme articles by relevance** — detail panel shows most recent first; should sort by keyword hit count + recency.

2. **Sub-topics filtering** — filter chips do nothing; decide: implement or remove.

3. **FA session renewal** — Drupal cookie expires 2026-05-23.

4. **Points of Return newsletter gap** — latest is 2 Apr; check forwarding rule.

---

## Build History

### 4 April 2026 (Session 41 — stats panel redesign + pub_date fix + HTML dedup)

**Stats panel full redesign (meridian.html)**
- Replaced entire #info-strip HTML with new 3-row layout
- White background (#fff), 2px solid #e0dbd0 border
- Row 1: 3 equal-width, equal-height columns (align-items:stretch, flex col with SVG flex:1)
  - Col 1: headline numbers (26px) + curation split bars (14px, % inside, label inline left)
  - Col 2: ingestion table with 24h / 48h / 7d / 14d columns
  - Col 3: 14-day sparkline with day+date two-row x-axis, weekends bolder
- Row 2: By Source / Full Text Coverage / By Topic (top 5) — equal padding, symmetric gutters
- Row 3: Option C style (bottom-rule header) — Last scraped / Unenriched backlog / 7-day rate / Agent activity
- Added `renderNewStats()` IIFE in JS — fully dynamic, populated from allArts on every load
- Source colours updated: FA changed to teal-green #2a7a5a (distinct from FT blue #1e4d8c)
- Legacy hidden IDs preserved for backward JS compatibility

**pub_date normalisation (server.py)**
- Added `normalize_pub_date()` — handles DD Month YYYY, Month D YYYY, Month YYYY, relative dates
- Called in `upsert_article()` on every write
- Enrichment prompt updated to request YYYY-MM-DD format
- One-off migration: Mac DB (24 rows), VPS DB (41 rows)

**Stats panel gap fix (meridian.html)**
- `recalcStickyTops()` was setting `top: 184px` on #info-strip (position:relative) — caused ghost gap + overlap
- Removed the `is_.style.top` assignment

**Duplicate HTML blocks removed (meridian.html)**
- Second copy of #key-themes-view, #briefing-view, #kt-brief-modal removed (lines 1607–1727)
- Orphaned `<div>Library</div>` heading removed
- File: 4848 → 4727 lines

### 4 April 2026 (Session 40 — filter row, stats fix, cleanup)
- Stats (📊) and Clip Bloomberg (📎) moved to filter row (row 4)
- #info-strip changed from position:sticky → position:relative
- Stale second #info-strip removed
- 66 tmp files purged; tmp_*.py, tmp_*.txt added to .gitignore

### 4 April 2026 (Session 39 — Major UI redesign)
- Card layout Option 3: fixed 44px date column
- Palette 1A: warm cream split, amber reserved
- Duplicate HTML bug (corrupted DOCTYPE) fixed

### 3 April 2026 (Session 38)
- Newsletter + interview VPS sync added
- Bloomberg source filter added

### 3 April 2026 (Session 37)
- Brief article selection redesigned
- FT enrichment, /api/enrich bug fix
- Chart backfill — 163 images confirmed

---

## GitHub Visibility
- Repo: PUBLIC — github.com/dakersalex/meridian-server
- Excluded: credentials.json, cookies.json, meridian.db, newsletter_sync.py, venv/, tmp_*.py, tmp_*.txt, *.bak*

## Session Starter Prompt
---
You are helping me build Meridian, my personal news aggregator. Please read my technical notes from the Filesystem MCP at /Users/alexdakers/meridian-server/NOTES.md and review them. Then run the session start health check.
---

Note for Claude: Read NOTES.md via Filesystem MCP (NOT GitHub URL — blocked).
NEVER ask Alex to run Terminal commands — run everything autonomously via shell bridge.
Never restart Flask via the shell endpoint.
After any large HTML patch, check: grep -c "<html lang" ~/meridian-server/meridian.html (should be 1).
JS syntax check: grep for key element IDs and function names — do NOT use ast.parse on HTML files.
