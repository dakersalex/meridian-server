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
| The Economist | 304 | ~270 |
| Financial Times | 191 | ~185 |
| Foreign Affairs | 69 | 69 |
| Bloomberg | 38 | 37 |
| Other | ~41 | — |
| **Total** | **~643** | **~603** |

VPS is the canonical DB. Mac local DB may differ slightly.

---

## pub_date Format
All pub_dates stored as ISO `YYYY-MM-DD`.
`normalize_pub_date()` in server.py handles incoming formats.
Session 45: remaining non-ISO stragglers fixed via one-off migration script.

### Economist pub_date issue (Session 45)
Economist URL dates (e.g. /2026/03/26/) are 1-3 days earlier than the edition date shown on the page.
Scraper uses URL date extraction — this causes systematic off-by-1-3 day errors for Economist articles.
Session 45 manually corrected 52 bookmark articles using the bookmarks page as ground truth.
TODO: fix Economist scraper to read pub_date from the article page (time[datetime] or meta tag) rather than URL.

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
The push script (in wake_and_sync.sh) originally only pushed `status='full_text'` articles.
This caused 8 Economist title_only articles from the 11-day gap to be missing from VPS.
Fixed in Session 45: push script now includes `status IN ('full_text','title_only','fetched','agent')`.

### meridian_sync.py — 415 bug (fixed Session 45)
`meridian_sync.py` was calling `requests.post('/api/sync')` with no body/Content-Type.
Flask requires Content-Type:application/json for request.json — returned 415 on every call.
**This broke syncing for 11 days (Mar 26 – Apr 6).** Fixed: added `json={}` to the POST call.

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
- economist.com is blocked for JS execution by MCP extension security rules — cannot touch Economist tabs even with MCP border visible

### Key patterns
- Write patch scripts via filesystem:write_file → execute via window.shell()
- Line-number patches are DANGEROUS — always use exact text str.replace()
- For large deletions, line-index slicing in Python (lines[:N] + lines[M:]) is safe when anchors verified first
- Syntax check for HTML/JS files: grep for key element IDs and function names — do NOT use ast.parse on HTML files
- Correct pre-deploy check: grep for key IDs, check HTML_LANG_COUNT=1, check DOCTYPE=1
- After deploying, verify via live site tab (Tab B)
- Check for duplicate `<html>` tags: `grep -c "<html lang" meridian.html` should return 1

### CRITICAL: Regex literals inside JS functions near backtick template literals
Never use regex literals (e.g. `/pattern/g`) inside any JS function that also contains or is near a backtick template literal string — use `.split('x').join('y')` instead.

### CRITICAL: Single quotes inside single-quoted JS string literals
Never use single-quoted outer JS strings containing single quotes — use double-quoted outer strings for HTML-building blocks.

### CRITICAL: Inline onmouseover/onmouseout for hover states
Never use inline `onmouseover`/`onmouseout` — always use CSS `:hover` classes instead.

### CRITICAL: Duplicate HTML bug prevention
After any patch replacing a large HTML block, always verify:
  grep -n "<!DOCTYPE\|<html lang" ~/meridian-server/meridian.html
Expected: line 1 only.

### tmp_ files
- tmp_*.py, tmp_*.txt, *.bak* are all gitignored
- Write scripts to ~/meridian-server/tmp_*.py, read output from tmp_*.txt
- Clean up at end of session: rm -f tmp_*.txt tmp_*.py

### Shell output keyword filter
The shell bridge swallows output containing certain words ("api", "fetch", "query string", etc.).
Workaround: write results to tmp_*.txt and read via Filesystem MCP.

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

### Row structure (sticky, stacked)
```
Row 1: Masthead — logo + tagline | date + synced time + dot + connected
Row 2: Folder-switcher — News Feed · Key Themes · Briefing Generator | Sync all · AI Analysis
Row 3: Main-nav — FEED · ARCHIVE · NEWSLETTERS · INTERVIEWS · SUGGESTED
Row 4: Filter — All articles · All curation · All sources · Last 6 months | 📊 Stats · 📎 Clip Bloomberg
Row 5: Info-strip (Stats panel, hidden by default, NOT sticky)
```

### Stats panel (#info-strip) — Session 45 state

**Row 1 — 3 columns (overflow-x:auto, min-width:860px):**
- Col 1: Article library — two sub-columns: left (Total/My saves/AI picks stacked), right (Full text)
- Col 2: 14-day swim lanes chart (HTML div, not SVG — supports hover tooltips)
- Col 3: "14 day total" — three swim-lane-style bars (FT/Economist/FA), 60px wide, centred, no labels/legend

**Swim lanes (Col 2) — Session 45:**
- HTML div layout (replaced SVG) — supports CSS :hover tooltips
- Shared globalMax scale across all three source lanes
- Total number above each bar; no AI count below
- Hover tooltip: dark grey bg, all white text, shows date / Total / AI picks / My saves
- Tooltip uses .sw-col / .sw-tip CSS classes injected into <head>
- overflow:visible on lane rows and bars wrapper so tooltips escape container
- Source labels: FT / Economist / FA (not Eco) at 11px bold

**Col 3 summary bars:**
- 3 lanes: FT (blue #1e4d8c), Economist (dark red #8b1a1a), FA (green #2a7a5a)
- Same LANE_H=20 / TICK_H=16 / LANE_GAP=10 spacing as swim lanes for row alignment
- 60px bar width, centred, total above, AI·My count below
- globalMax shared across all three sources
- No source labels or legend — reads as visual continuation of Col 2

**Row 2** — 3 equal columns: By source / Full text coverage / By topic
**Row 3** — 4 columns: Last scraped / Unenriched backlog / 7-day rate / Agent activity

**AI Health Check (top of Stats panel):**
- Flask endpoint POST /api/health-check proxies to Haiku
- Bloomberg explicitly excluded from all health check analysis (manual clip source, gaps are normal)
- Haiku system prompt updated to exclude Bloomberg from zero-day/trend/daysSinceLatest checks
- DOM IDs: sp-health-row, sp-health-eyebrow, sp-health-score, sp-health-summary, sp-health-issues, sp-health-ts

### Article card layout (Option 3 — fixed date column)
```
[date col 44px] [card-body flex:1]
                [card-header: source · topic | ✕ delete]
                [article-title (Playfair serif)]
                [article-summary]
                [card-footer: Full text badge · AI pick/My save · tags]
```

### Curation classification — Session 45 fix
`auto_saved` is now the single source of truth for AI pick vs My save throughout all UI.
`status='agent'` is no longer used for UI classification (kept in DB historically but ignored in JS).
Fixed expressions: all `a.auto_saved || a.status==='agent'` replaced with `a.auto_saved` across feed filters, swim lanes, stats counts, detail panel.

---

## Source-Specific Notes

### Financial Times
- Scraper: Playwright, `ft_profile/`
- Session expires periodically — manual re-login needed
- Typical cadence: 3–6 articles/day
- Saved articles page: ft.com/myft/saved-articles/... (chronological by save date)
- Agent picks: FT homepage scored by Haiku ≥8 → auto_saved=1
- **My save vs AI pick fix (Session 45):** FT scraper now demotes auto_saved=1 to 0 if article found in myFT saved list. score_and_autosave UPDATE now has AND auto_saved=0 guard — never promotes manual saves to AI picks.
- FT article pub_date: extracted from `meta[property='article:published_time']` or `time[datetime]` — works reliably when FT session is active.
- FT agent articles (status='agent') now included in enrich_title_only_articles query (was previously excluded, causing missing pub_dates).

### The Economist
- Scraper: Playwright, `economist_profile/`
- headless=False required (Cloudflare detection)
- Edition drops Tue/Thu/Sat
- Bookmarks page: economist.com/for-you/bookmarks (ordered by save date, newest first)
- Stop-on-first-existing logic is correct for bookmark page (chronological by save date)
- pub_date extracted from URL (/YYYY/MM/DD/) — systematically 1-3 days early vs page date
- 52 bookmarks manually corrected in Session 45 using actual page dates
- Cloudflare blocks headless Playwright — only warmed persistent profile at scheduled times works

### Foreign Affairs
- Scraper: Playwright, `fa_profile/`
- Session: Drupal cookie valid until **2026-05-23**
- Saved articles ordered chronologically by save date

### Bloomberg
- **No automated scraper — by design.** Bot detection was too strong; Playwright scraper removed.
- Articles added manually via Chrome Extension v1.3 (clip button in logged-in session).
- Gaps in Bloomberg ingestion are NORMAL — not a system fault.
- AI health check explicitly excludes Bloomberg from all analysis.
- Cadence depends entirely on manual clipping.

---

## Key Themes (KT) System
- 8 themes on VPS, sorted by article count descending
- 3-call architecture: Sonnet (theme gen) → Haiku (assignment) → Haiku (key_facts)
- KT lives on VPS only — Mac local DB has kt_themes table but always empty

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

### 🔴 Infrastructure / Stability
1. **Backup system** — No automated DB snapshots. Need: git tag on each deploy + daily cron copy of meridian.db (keep 7 days).
2. **deploy.sh — add git reset --hard HEAD** before pull to prevent VPS stash poisoning (crashed Flask 3x this session).
3. **Full code review** — Audit server.py and meridian.html for redundant endpoints, dead code, bugs. Dedicate a full session.

### 🔴 Ingestion / Sync
4. **Third sync window (~17:40)** — Add a third launchd sync window. Low risk, easy win.
5. **Economist pub_date scraper fix** — Read date from article page (meta tag) not URL. URL dates are 1-3 days early.

### 🟡 Briefing Generator
6. **Charts not referenced in briefing body text** — Need chart references woven into prose and relevance check per section.
7. **Data points need date anchors** — Stats like "down X% YTD" need explicit date reference.
8. **Briefing source section — add detail grid** — Articles per source, date range, sample method.

### 🟡 UI / Frontend
9. **Newsletter + Suggested sections — match Feed design** — Bring into line with card layout Option 3.
10. **Sort KT theme articles by relevance** — Currently date-sorted; should weight by keyword hit count + recency.
11. **Sub-topics filtering — implement or remove** — Filter chips render but do nothing.

### 🟡 Enrichment / Data
12. **FT enrichment backfill** — Some FT articles still unenriched. Run targeted backfill.
13. **KT tag-new wiring into VPS scheduler** — Incremental tagging built, not yet hooked into sync cycle.

### 🟢 Maintenance / Watch
14. **FA cookie renewal** — Drupal cookie expires 2026-05-23.
15. **Points of Return newsletter gap** — Latest issue 2 Apr. Check iCloud forwarding rule.
16. **Bloomberg ingestion** — Manual only. Check clipping still works.
17. **Clean up tmp_*.py / tmp_*.txt files** — rm -f tmp_*.txt tmp_*.py

---

## Build History

### 6 April 2026 (Session 45 — major bug fixes, data backfill, stats redesign)

**Critical: meridian_sync.py 415 bug fixed**
- `requests.post('/api/sync')` had no Content-Type header — Flask returned 415 on every call
- Broken for 11 days (Mar 26 – Apr 6) — all sync attempts silently failed
- Fix: added `json={}` to POST call. Deployed and verified.

**549 articles bulk-pushed to VPS**
- Mac local DB had 549 full_text articles not on VPS due to 415 bug
- Pushed via tmp_push.py using push-articles endpoint
- Subsequently: push script updated to include title_only/fetched/agent status articles too

**Agent articles fixed: pub_date and curation**
- `enrich_title_only_articles()` was excluding `status='agent'` articles — now includes them
- `score_and_autosave` UPDATE now has `AND auto_saved=0` guard — never overrides manual saves
- FT scraper now demotes auto_saved=1→0 when article found in myFT saved list
- 5 FT agent articles: pub_dates corrected by navigating to each URL in browser and reading meta tag
- 3 confirmed My saves (aria-pressed=true on FT), 2 confirmed AI picks

**Economist bookmark backfill (52 articles)**
- Cross-checked all 52 Economist bookmarks from the bookmark page against DB
- 19 missing articles inserted as title_only/My save
- 16 wrong dates corrected (URL date extraction systematic error)
- 5 wrong curations fixed (AI pick → My save)
- All pushed to VPS

**pub_date normalisation**
- 4 Economist articles with non-ISO pub_dates (DD Month YYYY format) fixed
- normalize_pub_date() now handles all incoming formats; DB clean

**VPS stash poisoning — permanently cleared**
- VPS had stale `text.split("\n")` broken literal-newline diff in git stash
- Was re-applied on every deploy, crashing Flask (3 incidents this session)
- Fixed via SCP patch script; stash cleared with `git stash clear`

**Bloomberg health check fix**
- Haiku system prompt updated to explicitly exclude Bloomberg from all analysis
- Bloomberg gaps are normal (manual clip only) — was incorrectly flagged as "dead scraper"

**Stats panel Row 1 redesign**
- Col 1: Article library restructured — two sub-columns (counts | full text), curation split removed
- Col 2: Swim lanes converted from SVG to HTML div layout — enables CSS hover tooltips
- Col 3: New "14 day total" — swim-lane style bars (FT/Eco/FA), 60px wide, centred, no labels
- Shared globalMax scale across all lanes (was per-lane)
- Total number above bars only; AI count removed from display
- Hover tooltip: dark grey bg, all white text, date/Total/AI/My breakdown
- Tooltip clipping fixed: overflow:visible on lane rows and bars wrapper
- Row 1 wrapped in overflow-x:auto with min-width:860px — prevents misalignment at narrow widths
- Source labels updated: Eco → Economist

**auto_saved as single source of truth**
- All JS expressions `a.auto_saved || a.status==='agent'` replaced with `a.auto_saved`
- Affects: swim lanes, feed filter, library counts, stats counts, detail panel, agent rate

**Session starter prompt updated**
- New prompt uses exact tool_search queries for reliable MCP loading

### 5 April 2026 (Session 44 — AI health check fully operational)
### 5 April 2026 (Session 43 — SyntaxError diagnosed)
### 5 April 2026 (Session 42 — stats headings, health check panel added)
### 4 April 2026 (Session 41 — stats panel redesign + pub_date fix + HTML dedup)
### 4 April 2026 (Session 40 — filter row, stats fix, cleanup)
### 4 April 2026 (Session 39 — Major UI redesign, Palette 1A, card layout Option 3)
### 3 April 2026 (Session 38 — Newsletter + interview VPS sync, Bloomberg filter)
### 3 April 2026 (Session 37 — Brief article selection, FT enrichment, chart backfill)

---

## GitHub Visibility
- Repo: PUBLIC — github.com/dakersalex/meridian-server
- Excluded: credentials.json, cookies.json, meridian.db, newsletter_sync.py, venv/, tmp_*.py, tmp_*.txt, *.bak*

## Session Starter Prompt

```
You are helping me build Meridian, my personal news aggregator.

## Step 1 — Load MCPs (do this first, before anything else)
Call tool_search with EXACTLY these queries in order:
1. "tabs context mcp" — loads Chrome MCP (gives you tabs_context_mcp, javascript_tool, navigate)
2. "filesystem write file" — loads Filesystem MCP (gives you filesystem:write_file, filesystem:read_text_file)

Do not attempt to read files or touch the browser until both tool_searches have completed.

## Step 2 — Read NOTES.md
Read /Users/alexdakers/meridian-server/NOTES.md via filesystem:read_text_file.

## Step 3 — Set up browser tabs
Call tabs_context_mcp with createIfEmpty:true to get current tab IDs (they change every session).
Tab A = localhost:8080/meridian.html (shell bridge)
Tab B = meridianreader.com/meridian.html (live verify)

## Step 4 — Inject shell bridge into Tab A
Run this via javascript_tool on Tab A:
window.shell = (cmd) => fetch('http://localhost:4242/api/dev/shell', {
  method:'POST', headers:{'Content-Type':'application/json'},
  body:JSON.stringify({cmd})
}).then(r=>r.json());

## Step 5 — Health check
Write the health check script via filesystem:write_file to ~/meridian-server/tmp_health.py,
then execute it via shell bridge: window.shell("python3 ~/meridian-server/tmp_health.py > ~/meridian-server/tmp_hc_out.txt 2>&1; echo done")
Then read the result via filesystem:read_text_file.

NEVER attempt to run a Python script before the shell bridge is injected.
NEVER ask me to run Terminal commands — do everything autonomously.
```

Note for Claude: Read NOTES.md via Filesystem MCP (NOT GitHub URL — blocked).
NEVER ask Alex to run Terminal commands — run everything autonomously via shell bridge.
Never restart Flask via the shell endpoint.
After any large HTML patch, check: grep -c "<html lang" ~/meridian-server/meridian.html (should be 1).
JS syntax check: grep for key element IDs and function names — do NOT use ast.parse on HTML files.
NEVER use regex literals inside functions near backtick template literal strings — use .split().join() instead.
NEVER use single-quoted outer JS strings containing single quotes — use double-quoted outer strings for HTML-building blocks.
NEVER use inline onmouseover/onmouseout for hover styling — use CSS :hover classes instead.
economist.com is blocked for JS execution by MCP — cannot run javascript_tool on Economist tabs.
