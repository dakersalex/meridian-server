# Meridian — Technical Notes
Last updated: 5 April 2026 (Session 44 — runHealthCheck SyntaxError fixed, site restored)

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

## Database (5 April 2026 — VPS)
| Source | Total | Full text |
|---|---|---|
| The Economist | 273 | ~265 |
| Financial Times | 181 | ~179 |
| Foreign Affairs | 66 | 57 |
| Bloomberg | 38 | 37 |
| Other | ~19 | — |
| **Total** | **~577** | **~541** |

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

### CRITICAL: Regex literals inside JS functions that share scope with backtick template literals
**Do not use regex literals (e.g. `/pattern/g`) inside any JS function that also contains or is near a backtick template literal string.** The browser parser can misread the backtick as closing the template, causing `SyntaxError: Invalid regular expression`. This bit us in Session 42 with `runHealthCheck()`.
**Fix: always use `.split('x').join('y')` instead of `.replace(/x/g, 'y')` in these contexts. Use plain string concatenation for multi-line strings instead of template literals.**

### CRITICAL: Single quotes inside single-quoted JS string literals
**Do not use single-quoted JS strings when the string content contains single quotes** (e.g. CSS font-family values like `'IBM Plex Sans'`, or hover style strings like `'#faf8f4'`). The parser will terminate the string early, causing `SyntaxError: Unexpected identifier`.
**Fix: use double-quoted outer strings for any JS string literals that build HTML or inline CSS. This entirely avoids the escaping problem. For HTML-building blocks (innerHTML builders, button constructors), always use double-quoted outer JS strings.**

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

## UI Design — Current State (Session 42)

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

### Stats panel (#info-strip) — updated Session 42
Background: `#fff` (white), bottom border: `2px solid #e0dbd0`
Toggled by 📊 Stats button in filter row. Rendered by `renderNewStats()` (IIFE called in loadAll).
Health check fired by `runHealthCheck()` — called from `toggleStatsStrip()` on open (once per session, cached in `window._healthCache`). Refresh button forces a new call.

**Health check row (Row 0)** — amber left border panel above all stats rows:
- Eyebrow: "AI health check · HH:MM" (9px uppercase amber)
- Summary: 2–3 sentence plain English overview (12px)
- Issues: clickable button rows — hover reveals "↗ ask Claude", click stores prompt in `window._hcPrompts[idx]` and calls `window.sendPrompt()`
- Score: X/10 top-right, colour coded green/amber/red
- Refresh button + timestamp
- DOM IDs: sp-health-row, sp-health-eyebrow, sp-health-summary, sp-health-issues, sp-health-score, sp-health-ts

**Issue button implementation note (Session 44):** onclick uses `window._hcPrompts` index store (not inline prompt strings) to avoid all quoting issues. `issIdx` counter increments per issue; prompts stored in `window._hcPrompts = {}` before the map.

**Unified section heading style (all rows)**: `font-size:9px; font-weight:700; letter-spacing:1.2px; text-transform:uppercase; color:#8a8a8a; border-bottom:1px solid rgba(0,0,0,.1); padding-bottom:5px; margin-bottom:9px`
- Applied consistently to: Article library, Curation split, New articles, 14-day ingestion, By source, Full text coverage, By topic, Last scraped, Unenriched backlog, 7-day rate, Agent activity
- Col 1 of Row 1 now has "Article library" heading (was untitled before)
- Row 3 previously used dark `#1a1a1a` rule — now uses the same muted grey as all other headings

**Row 1** — 3 equal columns (`grid-template-columns: 1fr 1fr 1fr`, `align-items: stretch`):
- **Col 1**: "Article library" heading + Headline numbers (Total / My saves / AI picks / Full text, 26px bold) + "Curation split" heading + 3 bars (All time / 30 days / 7 days)
- **Col 2**: "New articles" heading + ingestion table (24h / 48h / 7d / 14d)
- **Col 3**: "14-day ingestion" heading + sparkline SVG (flex:1)

**Row 2** — 3 equal columns:
- By source / Full text coverage / By topic (top 5)

**Row 3** — 4 columns:
- Last scraped / Unenriched backlog / 7-day rate / Agent activity

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

### 5 April 2026 (Session 44 — runHealthCheck SyntaxError fixed)

**runHealthCheck() fully repaired (two deploys)**

Deploy 1 — three fixes to eliminate regex/backtick conflicts:
- Fix 1: Replaced backtick template literal for Haiku `system:` value with IIFE + plain string concatenation (`var s = '...'; s += '...'; return s;`)
- Fix 2: Replaced `.replace(/\//g,...)`, `.replace(/\`/g,...)`, `.replace(/\$/g,...)` regex calls in `safePrompt` line with `.split().join()` equivalents
- Fix 3: Rewrote `onclick` handler — removed backtick `sendPrompt(\`...\`)` call

Deploy 2 — fix exposed pre-existing bug in issue-button builder:
- Root cause: lines 3791–3793 used single-quoted outer JS strings containing unescaped single quotes (`'IBM Plex Sans'`, `'#faf8f4'`, etc.), causing `SyntaxError: Unexpected identifier 'IBM'`
- Fix: rewrote entire `issEl.innerHTML` map block using double-quoted outer strings throughout
- Prompts now stored in `window._hcPrompts[issIdx]` (index store) rather than embedded in onclick attribute strings — cleaner and avoids all future quoting issues
- `font-family:IBM Plex Sans,sans-serif` (no quotes needed in inline CSS)

Site confirmed working: 480 articles load, no SyntaxErrors in console.

### 5 April 2026 (Session 43 — SyntaxError diagnosed, patch designed but not yet applied)

**runHealthCheck SyntaxError — full diagnosis**
- Confirmed: site stuck on "Checking…" due to `SyntaxError: Invalid regular expression` in `runHealthCheck()`
- Root cause: backtick template literal for the Haiku `system:` prompt string, plus regex literals (`.replace(/x/g,y)`) in the `safePrompt` building block, inside the same function scope
- Fix designed (not yet applied): replace backtick system string with `var s = '...' + '...'` concatenation; replace all three `.replace(/regex/)` calls with `.split().join()`; rewrite `onclick` to use single-quoted `sendPrompt('...')` instead of backtick
- Session ended before patch script could be executed (tool call limit reached during filesystem:write_file tool_search)

### 5 April 2026 (Session 42 — stats headings unified, AI health check panel)

**Stats panel heading unification (meridian.html)**
- All section headings now use one consistent style: 9px, 700 weight, 1.2px tracking, uppercase, #8a8a8a, with `border-bottom:1px solid rgba(0,0,0,.1)` rule
- Previously Row 1/2 had no rule, Row 3 used heavy `#1a1a1a` rule — all now match
- Col 1 of Row 1 given "Article library" heading (was previously untitled)
- Row 2 top border/padding removed to align visually with Row 1

**AI health check panel added (meridian.html)**
- New `#sp-health-row` HTML block inserted above Row 1 inside #info-strip
- `window.runHealthCheck(force)` async function added — calls Haiku with computed stats payload, renders summary + scored issues
- Issues are clickable buttons — hover reveals "↗ ask Claude", click calls `sendPrompt()` via prompt index store
- Cached in `window._healthCache`, cleared on page reload; Refresh button forces new call
- `toggleStatsStrip()` updated to call `runHealthCheck(false)` on panel open

### 4 April 2026 (Session 41 — stats panel redesign + pub_date fix + HTML dedup)
- Stats panel full redesign (3-row layout, white bg, sparkline, ingestion table)
- pub_date normalised to ISO YYYY-MM-DD everywhere
- Duplicate HTML blocks removed (4727 lines)

### 4 April 2026 (Session 40 — filter row, stats fix, cleanup)
- Stats (📊) and Clip Bloomberg (📎) moved to filter row (row 4)
- #info-strip changed from position:sticky → position:relative
- 66 tmp files purged

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
NEVER use regex literals inside functions that contain or are near backtick template literal strings — use .split().join() instead.
NEVER use single-quoted outer JS strings when the content contains single quotes (CSS values, font names, colour hex strings in hover handlers) — use double-quoted outer strings for all HTML-building blocks.
