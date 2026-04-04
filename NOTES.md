# Meridian — Technical Notes
Last updated: 4 April 2026 (Session 39 — major UI redesign: card layout, palette, stats panel)

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
| The Economist | 270 | 264 |
| Financial Times | 177 | 171 |
| Foreign Affairs | 66 | 57 |
| Bloomberg | 38 | 37 |
| Other | ~41 | — |
| **Total** | **592** | **539** |

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
- Always python3 -m py_compile is NOT available on this stack — do JS syntax check instead
- After deploying, verify via live site tab (Tab B)
- Check for duplicate `<html>` tags after any major HTML restructuring: `grep -c "<html" meridian.html` should return 1

### CRITICAL: Duplicate HTML bug prevention
The dedup bug (session 39) caused the whole page to render twice because a Python
patch script corrupted `<!DOCTYPE html>` into `TYPE html>`. After any patch that
replaces a large HTML block, always run:
  grep -n "<!DOCTYPE\|<html lang" ~/meridian-server/meridian.html
Expected: line 1 only (plus any inside JS template strings). Never deploy if there
are two `<html lang` tags in the file.

---

## UI Design — Current State (Session 39)

### Colour Palette (Palette 1A)
```css
--paper: #faf8f4          /* content zone: cards, sidebar, feed area */
--paper-2: #f0ece3        /* header rows: masthead, nav, sub-nav, filter */
--paper-3: #e4dfd4        /* badges, neutral elements */
--accent: #c4783a         /* logo "dian", AI Analysis button, card hover border */
--ink: #1a1a1a            /* active tab underline, active badge, headings */
--green: #2d6b45          /* full text badge, live activity pills, full text coverage */
--rule: rgba(0,0,0,0.1)  /* dividers */
```

- **Header rows** (rows 1-5): background `var(--paper-2)` — darker warm cream
- **Content zone** (cards, sidebar, feed area): background `var(--paper)` — lighter warm cream
- **Amber** appears ONLY in: logo "dian", AI Analysis button, card hover border
- **Sync all button**: `background: #d4976a` (muted amber fill, no border)
- **Activity pills**: green when active, neutral grey when zero — never amber
- **AI picks count (row 4)**: plain bold ink, NOT amber
- **Filter dropdowns**: white bg (`var(--paper)`), `1px rgba(0,0,0,0.25)` border

### Row structure (sticky, stacked)
```
Row 1: Masthead — logo + tagline | date + synced time + green/red dot + connected
Row 2: Folder-switcher — News Feed · Key Themes · Briefing Generator | Stats · Clip Bloomberg · Sync all · AI Analysis
Row 3: Main-nav — FEED 471 · ARCHIVE · NEWSLETTERS · INTERVIEWS · SUGGESTED
Row 4: Filter — All articles · All curation · All sources · Last 6 months
Row 5: Info-strip (Stats panel, hidden by default, toggled by Stats button)
```

### Sticky top values (px, from recalcStickyTops())
- Masthead: top 0 (h≈68)
- Folder-switcher: top 67 (h≈44)
- Main-nav: top 111 (h≈35)
- Filter row: top 146 (h≈41)
- Info-strip: top 184 (shows below filter when visible)

### recalcStickyTops() — IMPORTANT
New order after session 39 swap (filter above info-strip):
```js
// fh = feed-header-outer (filter), is_ = info-strip
fh.style.top = (h0+h1+h2-3)+'px';
if (is_) is_.style.top = (h0+h1+h2+h3-4)+'px';  // h3 = filter height
```
Run on load + resize. Info-strip visibility is tracked; filter always visible.

### Stats toggle (Info-strip)
- Button: `#stats-toggle-btn` in folder-switcher row
- Function: `toggleStatsStrip()` — toggles `display:none`/`display:flex` and calls `recalcStickyTops()`
- Hidden by default on page load
- Stats panel background = `var(--paper)` (same as card area — intentional, blends in)
- Bottom border: `3px solid var(--ink)` — strong separation from feed below

### Stats panel layout (two-row)
**Top row** (headline numbers + 24h):
- 592 Total · 482 My saves · 110 AI picks · 539 Full text (22px bold)
- 24h activity: `FT +10 · Economist +2 · FA +5 · Bloomberg — · FP —` (10px, source colours)
- 24h uses date string comparison: `a.pub_date >= yesterdayStr` (pub_date is YYYY-MM-DD, no time)

**Bottom row** (charts):
- Curation split donut (80px): AI arc = full amber ring, saves arc on top with `transform="rotate(-90 40 40)"`
  - `stroke-dasharray = savePct * 201.062` — exact two segments, no gap
- Top 5 topics (colour dots)
- By source (horizontal bars, source brand colours)
- Full text coverage (green bars, gold/red for low coverage)

### Article card layout (Option 3 — fixed date column)
```
[date col 44px] [card-body flex:1]
                [card-header: source · topic | ✕ delete btn]
                [article-title (Playfair serif)]
                [article-summary]
                [card-footer: Full text badge · AI pick/My save · tags]
```
- `card-inner`: `padding: 16px 20px 16px 17px` (17px left compensates for 3px hover border)
- Card hover: `border-left: 3px solid var(--accent)` slides in via `border-left-color 0.15s`
- Delete button: `card-del` class — 20×20px grey square box, top-right of card-body
- Featured card (first): same layout, no "Latest · FT" label, slightly larger title

### Curation badges
- AI pick: `.curation-ai` — `background: #f5ede4; color: #854f0b; border: 0.5px solid #e8c9a8`
- My save: `.curation-my` — `background: var(--paper-3); color: var(--ink-3); border: 0.5px solid var(--rule)`
- `autoPill` JS: `a.auto_saved ? 'AI pick' : 'My save'` (plain text, used in curation-badge span)

### Nav dot colours
- Active nav: `background: var(--accent)` amber dot
- Inactive nav: `background: var(--paper-3)` grey dot

### Server status
- ONE instance only: in masthead right, below date
- Format: `Synced 10:08 • meridianreader.com · connected`
- Green dot when connected (`status-dot.connected`), red when error
- Removed from folder-switcher row (was duplicated)

---

## Source-Specific Notes

### Financial Times
- Scraper: Playwright, `ft_profile/`
- Session expires periodically — manual re-login needed

### The Economist
- Scraper: Playwright, `economist_profile/`
- headless=False required (Cloudflare detection)

### Foreign Affairs
- Scraper: Playwright, `fa_profile/`
- Session: Drupal cookie valid until **2026-05-23**

### Bloomberg
- No automated scraper — Chrome Extension v1.3 only

---

## Key Themes (KT) System
- 8 themes on VPS, sorted by article count
- 3-call architecture: Sonnet (theme gen) → Haiku (assignment) → Haiku (key_facts)

---

## Outstanding Issues / Next Steps

1. **"LIBRARY" text node** — a bare text node appears just above the feed after the stats strip.
   Not in the HTML file (confirmed by grep) — may be a lingering DOM artefact from the
   duplicate-page bug. Hard reload clears it but it returns. Find the source — likely a
   stray text node near the info-strip/main-layout boundary.

2. **Sort theme articles by relevance** — detail panel shows most recent first; sort by
   keyword hit count + recency.

3. **Sub-topics filtering** — filter chips do nothing; decide implement or remove.

4. **FA session renewal** — Drupal cookie expires 2026-05-23.

5. **Points of Return newsletter gap** — latest is 2 Apr; check forwarding rule.

6. **Tmp file cleanup** — accumulated during long sessions.

7. **Stats panel: 24h activity** — currently comparing `pub_date >= yesterdayStr`.
   Works correctly for articles with pub_date set. Fallback uses saved_at timestamp.

---

## Build History

### 4 April 2026 (Session 39 — Major UI redesign)

**Card layout (Option 3)**
- Fixed 44px date column on left, card-body on right
- Source · Topic header with boxed delete button top-right
- Status + curation badges below summary
- Amber left border slides in on hover (3px, `border-left-color 0.15s`)
- Removed "Latest · FT" label from first card

**Palette 1A**
- Warm cream headers (#f0ece3 / paper-2), lighter warm content area (#faf8f4 / paper)
- Amber reserved for: logo accent, AI Analysis button, card hover border ONLY
- All other active states use ink (#1a1a1a)
- Activity pills: green not amber
- AI picks count in row 4: bold ink, not amber
- Sync all: muted amber fill (#d4976a)
- Filter dropdowns: white bg, bolder border
- Single server status in masthead (green dot), removed from nav row

**Stats panel (major build)**
- Stats chip in nav row toggles info-strip panel
- Sync all + Clip Bloomberg moved from info-strip to nav row
- Info-strip hidden by default; toggled by Stats chip
- Two-row layout: numbers+24h (top) / donut+charts (bottom)
- 80px donut: correct two-segment SVG using full amber ring + rotate(-90) saves arc
- Top 5 topics (was 7)
- 24h: date string comparison fixes zero-article bug
- Bottom border 3px ink for clear separation from feed
- Background matches content zone (paper), not header zone (paper-2)

**Filter row reordering**
- Filter row moved ABOVE info-strip (was below)
- recalcStickyTops() updated to reflect new order

**Bug fixes**
- JS syntax error (missing semicolons before return in checkServer) — fixed
- Duplicate HTML bug caused by corrupted DOCTYPE during dedup — fixed
- Sticky row gap: 1px overlap per row, recalcStickyTops() now header-aware

### 3 April 2026 (Session 38 — UI redesign, sync pipeline, source panel)
- 2D nav with dot+background pattern
- Merged tally + activity into info-strip
- Newsletter + interview VPS sync added
- Bloomberg source filter added

### 3 April 2026 (Session 37)
- Brief article selection redesigned (score-based, recency, temporal anchor)
- FT enrichment, /api/enrich bug fix
- Chart backfill — 163 images confirmed ceiling

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
After any large HTML patch, always check: grep -c "<html lang" ~/meridian-server/meridian.html (should be 1).
