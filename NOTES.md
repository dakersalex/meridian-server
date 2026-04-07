# Meridian — Technical Notes
Last updated: 6 April 2026 (Session 45 — major bug fixes, data backfill, stats panel redesign)

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

### CRITICAL: VPS git stash poison
The VPS accumulates local diffs when we SCP patch files directly (bypassing git) to recover from crashes.
These diffs get stashed and re-applied on subsequent deploys, crashing Flask.
Fix: always use `git reset --hard HEAD && git pull` (not `git stash && git pull`) on VPS.
TODO: add `git reset --hard HEAD` to deploy.sh before the pull step to prevent this permanently.

## Database (6 April 2026 — VPS after Session 45 backfill)
| Source | Total | Full text |
|---|---|---|
| The Economist | 306 | ~270 |
| Financial Times | 191 | ~185 |
| Foreign Affairs | 61 | 59 |
| Bloomberg | 38 | 37 |
| Other | ~51 | — |
| **Total** | **~647** | **~603** |

VPS is the canonical DB. Mac local DB may differ slightly.

---

## pub_date Format
All pub_dates stored as ISO `YYYY-MM-DD`.
`normalize_pub_date()` in server.py handles incoming formats.

### Economist pub_date policy (decided Session 45)
URL date is ground truth for Economist. URL dates (/YYYY/MM/DD/) are the online publication date.
The bookmark page shows print edition dates (1-3 days later) — these are NOT used.
This is now consistent across all Economist articles in the DB.

### FA pub_date
FA saved articles page shows issue dates (Mar/Apr 2026 etc) but some articles have explicit online dates.
Use whichever date is shown on the actual article page.

---

## Curation Classification — IMPORTANT
`auto_saved` is the single source of truth for AI pick vs My save:
- `auto_saved=1` = AI pick (scored ≥8 by Haiku on FT/Economist homepage)
- `auto_saved=0` = My save (manually saved by user, or any FA/Bloomberg article)

### FA and Bloomberg — NEVER auto_saved=1
FA: scraper reads saved articles page only — all FA articles must be auto_saved=0 (My saves).
Bloomberg: manual Chrome extension only — all Bloomberg articles must be auto_saved=0.
`score_and_autosave` only scores `source IN ('Financial Times', 'The Economist')`.
Session 45: 14 FA articles incorrectly marked auto_saved=1 — all reset to 0.

### FA AI picks — future plan
To add AI picking for FA, need to:
1. Add Playwright homepage pass for foreignaffairs.com using fa_profile
2. Score visible articles with Haiku ≥8
3. Only then set auto_saved=1 for FA articles
FA homepage is JS-rendered — need Playwright, not DOM scraping.

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

Sync windows (Geneva time): 05:35 and 11:35.

### CRITICAL: Push script must include title_only articles
The push script must include `status IN ('full_text','title_only','fetched','agent')`.
Session 45: fixed after 415 bug recovery.

### meridian_sync.py — 415 bug (fixed Session 45)
`requests.post('/api/sync')` had no Content-Type — Flask returned 415.
Fix: added `json={}`. Was broken 11 days (Mar 26–Apr 6).

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
- economist.com is blocked for JS execution by MCP extension — cannot navigate there via MCP
- foreignaffairs.com IS accessible via MCP (Tab B or new tab)

### Key patterns
- Write patch scripts via filesystem:write_file → execute via window.shell()
- Always use exact text str.replace() — never line-number patches
- Pre-deploy check: `grep -c "<html lang" meridian.html` must return 1
- Shell bridge filters output containing "api", "fetch" etc — write to tmp_*.txt
- After any HTML patch, verify with grep for key element IDs

### CRITICAL: Regex literals inside JS functions near backtick template literals
Use `.split('x').join('y')` instead of regex literals.

### CRITICAL: Single quotes inside single-quoted JS string literals
Use double-quoted outer strings for HTML-building blocks.

### CRITICAL: Duplicate HTML bug prevention
After any large patch: `grep -n "<!DOCTYPE\|<html lang" ~/meridian-server/meridian.html`
Expected: line 1 only.

### tmp_ files
All gitignored. Clean up at end of session: `rm -f tmp_*.txt tmp_*.py`

---

## UI Design — Current State (Session 45)

### Colour Palette (Palette 1A)
```css
--paper: #faf8f4
--paper-2: #f0ece3
--paper-3: #e4dfd4
--accent: #c4783a
--ink: #1a1a1a
--green: #2d6b45
--rule: rgba(0,0,0,0.1)
```

### Stats Panel — Row 1 (final state after Session 45)

**Grid: `150px 1fr 1fr` with `overflow:visible`, `min-width:860px`**

**Col 1 — "Library" (150px fixed):**
- Single column layout, no sub-columns
- Title: "Library"
- 647 / Articles (no %)
- 560 / My saves / 87% (right-aligned, fixed 32px width)
- 87 / AI picks / 13% (right-aligned, fixed 32px width)
- Divider
- 603 / Full text / 93% (right-aligned, fixed 32px width)
- % figures are vertically centred alongside numbers (align-items:center)
- JS populates: sp-total, sp-saves, sp-saves-pct, sp-ai, sp-ai-pct, sp-ft, sp-ft-pct

**Col 2 — Swim lanes (1fr):**
- HTML div layout (not SVG) — supports CSS :hover tooltips
- LANE_H=40, TICK_H=16, LANE_GAP=20, YAW=72, bW=39, bG=3
- Shared globalMax scale across all three source lanes
- Total number above each bar (centred), no AI count below
- Hover tooltip: dark grey bg (#444), all white text, shows date/Total/AI/My
- Tooltip CSS injected into <head> as #sw-tip-style
- overflow:visible on sp-row1, lane rows, and bars wrapper
- Source labels: FT / Economist / FA at 11px bold (not Eco)
- Legend: centred below chart

**Col 3 — "14 Day Total" (1fr):**
- 3 swim-lane-style bars: FT (blue #1e4d8c), Economist (dark red #8b1a1a), FA (green #2a7a5a)
- LANE_H=40, TICK_H=16, LANE_GAP=20
- 60px bar width, total centred above, AI% in source colour to right of bar on same line
- globalMax shared across all 3 sources
- No source labels — reads as continuation of Col 2
- Summary below bars (after divider):
  - Total count centred in 60px, label "Total" to right
  - AI% centred in 60px, label "AI selected" to right
- DOM: sp-split-bars, sp-split-summary

**Row 2** — 3 equal columns: By source / Full text coverage / By topic
**Row 3** — 4 columns: Last scraped / Unenriched backlog / 7-day rate / Agent activity

**AI Health Check (top of Stats panel):**
- Bloomberg explicitly excluded from all health check analysis
- max_tokens: 1800, brevity constraints in system prompt
- DOM IDs: sp-health-row, sp-health-score, sp-health-summary, sp-health-issues

### Article card layout (Option 3 — fixed date column)
```
[date col 44px] [card-body flex:1]
                [card-header: source · topic | ✕ delete]
                [article-title (Playfair serif)]
                [article-summary]
                [card-footer: Full text badge · AI pick/My save · tags]
```

---

## Source-Specific Notes

### Financial Times
- Scraper: Playwright, `ft_profile/`
- Agent picks: FT homepage scored by Haiku ≥8 → auto_saved=1
- FT scraper demotes auto_saved=1→0 if article found in myFT saved list
- score_and_autosave has AND auto_saved=0 guard

### The Economist
- Scraper: Playwright, `economist_profile/`, headless=False required
- Edition drops Tue/Thu/Sat
- pub_date: URL date is ground truth (/YYYY/MM/DD/)
- Bookmark page dates are print edition dates — NOT used
- Cloudflare blocks headless — only warmed persistent profile works
- Homepage scoring: Haiku ≥8 → auto_saved=1

### Foreign Affairs
- Scraper: Playwright, `fa_profile/`
- Session: Drupal cookie valid until **2026-05-23**
- Reads saved articles page only — ALL FA articles are My saves (auto_saved=0)
- No homepage AI scoring (yet) — see FA AI picks plan above
- FA homepage is JS-rendered, needs Playwright for scraping
- Session 45: 14 FA articles incorrectly marked AI pick — all fixed to My save

### Bloomberg
- Manual Chrome extension clip only — all My saves (auto_saved=0)
- Gaps in Bloomberg ingestion are NORMAL
- Bloomberg excluded from all health check analysis

---

## Key Themes (KT) System
- 8 themes on VPS, sorted by article count descending
- 3-call architecture: Sonnet (theme gen) → Haiku (assignment) → Haiku (key_facts)
- KT lives on VPS only — Mac local DB has kt_themes table but always empty

---

## Outstanding Issues / Next Steps

### 🔴 Infrastructure / Stability
1. **Backup system** — No automated DB snapshots
2. **deploy.sh — add git reset --hard HEAD** before pull to prevent VPS stash poisoning
3. **Full code review** — Audit server.py and meridian.html for redundant code

### 🔴 Ingestion / Sync
4. **Third sync window (~17:40)** — Easy addition to launchd
5. **FA homepage AI scoring** — Add Playwright homepage pass using fa_profile (logged in). FA homepage is JS-rendered. Score with Haiku ≥8 → auto_saved=1. Do NOT add without homepage scraping.
6. **Economist pub_date scraper fix** — Scraper currently uses URL date which IS correct per policy. No fix needed.

### 🟡 Briefing Generator
7. **Charts not referenced in briefing prose**
8. **Data points need date anchors**
9. **Briefing source section detail grid**

### 🟡 UI / Frontend
10. **Newsletter + Suggested sections — match Feed design**
11. **Sort KT theme articles by relevance**
12. **Sub-topics filtering — implement or remove**

### 🟡 Enrichment / Data
13. **FT enrichment backfill** — Some FT articles still unenriched
14. **KT tag-new wiring into VPS scheduler**

### 🟢 Maintenance / Watch
15. **FA cookie renewal** — Drupal cookie expires 2026-05-23
16. **Points of Return newsletter gap** — Check iCloud forwarding rule
17. **Bloomberg ingestion** — Check clipping still works
18. **Clean up tmp_*.py / tmp_*.txt files**

---

## Build History

### 6 April 2026 (Session 45 — major bug fixes, data backfill, stats redesign)

**Critical: meridian_sync.py 415 bug fixed** — broken 11 days, 549 articles bulk-pushed to VPS

**Curation classification fixes:**
- auto_saved is single source of truth everywhere
- FA: all 14 incorrectly marked AI picks reset to My saves (on Mac and VPS directly)
- score_and_autosave: confirmed FA/Bloomberg excluded, clarifying comment added
- FT scraper: demotes auto_saved=1→0 when found in myFT saved list
- score_and_autosave: AND auto_saved=0 guard added

**Economist bookmark backfill (62 bookmarks total):**
- 52 corrected in earlier pass (19 missing, 16 wrong dates, 5 wrong curation)
- 10 more from second page paste: 2 missing inserted, 4 date fixes confirmed correct (URL date policy)
- URL date = ground truth for Economist (decided and documented)

**FA investigation:**
- All 36 FA saved articles confirmed in DB
- 3 "ghost" FA articles kept — likely older saves that scrolled off FA page
- FA homepage is JS-rendered, sparse via DOM scraping — needs Playwright for future AI scoring
- FA saved articles page accessible via MCP (foreignaffairs.com not blocked)

**Stats panel Row 1 — full redesign:**
- Col 1: "Library" — single column, 150px fixed, Total/My saves/AI picks/Full text with right-aligned %
- Col 2: Swim lanes — LANE_H=40, LANE_GAP=20, HTML div, hover tooltips, shared scale
- Col 3: "14 Day Total" — 3 swim-lane bars, AI% adjacent to bar, summary (total+AI%) below
- Grid: 150px 1fr 1fr, overflow:visible, min-width:860px
- Tooltip: dark grey #444 bg, all white text, overflow:visible on all containers
- Source labels: Economist (not Eco)

**VPS stash poisoning — cleared** — git stash clear, recovered via direct SSH python3 fix

**Bloomberg health check fix** — Haiku system prompt excludes Bloomberg from all analysis

### Previous sessions
Session 44 — AI health check fully operational
Session 43 — SyntaxError diagnosed
Session 42 — stats headings, health check panel added
Session 41 — stats panel redesign + pub_date fix + HTML dedup
Session 40 — filter row, stats fix, cleanup
Session 39 — Major UI redesign, Palette 1A, card layout Option 3
Session 38 — Newsletter + interview VPS sync, Bloomberg filter
Session 37 — Brief article selection, FT enrichment, chart backfill

---

## GitHub Visibility
- Repo: PUBLIC — github.com/dakersalex/meridian-server
- Excluded: credentials.json, cookies.json, meridian.db, newsletter_sync.py, venv/, tmp_*.py, tmp_*.txt, *.bak*

## Session Starter Prompt

**Alex's opening message (copy this exactly):**
```
Meridian session start. Read NOTES.md and run the startup sequence.
```

**Claude's startup sequence (defined here so NOTES.md is the single source of truth):**

### Step 1 — Load MCPs
Call tool_search with EXACTLY these queries in order:
1. `"javascript tool navigate tabs"` — loads Chrome MCP (NOT "tabs context mcp" — that query fails)
2. `"filesystem write file"` — loads Filesystem MCP

### Step 2 — Read NOTES.md
Read /Users/alexdakers/meridian-server/NOTES.md via filesystem:read_text_file.

### Step 3 — Set up browser tabs
Call tabs_context_mcp with createIfEmpty:true to get current tab IDs.
Tab A = localhost:8080/meridian.html (shell bridge)
Tab B = meridianreader.com/meridian.html (live verify)

### Step 4 — Inject shell bridge into Tab A
window.shell = (cmd) => fetch('http://localhost:4242/api/dev/shell', {
  method:'POST', headers:{'Content-Type':'application/json'},
  body:JSON.stringify({cmd})
}).then(r=>r.json());

### Step 5 — Health check
Write tmp_health.py via filesystem:write_file, execute via shell bridge, read result via filesystem:read_text_file.
Health check should report: total articles, full text count, unenriched count (excl Bloomberg), My saves vs AI picks, by-source breakdown, last 7 days by source, KT theme count.

### Standing rules
- NEVER ask Alex to run Terminal commands — do everything autonomously
- NEVER restart Flask via the shell endpoint (kills the process)
- After any large HTML patch: grep -c "<html lang" ~/meridian-server/meridian.html must return 1
- economist.com is blocked for JS execution by MCP extension
- foreignaffairs.com IS accessible via MCP
