# Meridian — Technical Notes
Last updated: 6 April 2026 (Session 45 — Bloomberg health check fix, consolidated to-do list)

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

## Database (6 April 2026 — Mac local)
| Source | Total | Full text | Enriched |
|---|---|---|---|
| The Economist | 277 | 271 | 271 (97%) |
| Financial Times | 185 | 178 | 153 (82%) |
| Foreign Affairs | 58 | 58 | 56 (96%) |
| Bloomberg | 38 | 37 | 36 (94%) |
| Other sources | 19 | — | — |
| **Total** | **577** | — | **533** |

VPS totals are higher (~602 as of Session 44) — VPS is the canonical DB.

---

## pub_date Format (normalised Session 41)
All pub_dates stored as ISO `YYYY-MM-DD` in both Mac and VPS databases.
`normalize_pub_date()` in server.py handles all incoming formats.
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

Sync windows (Geneva time): 05:35 and 11:35. Third window at ~17:40 is under consideration.

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
- Syntax check for HTML/JS files: grep for key element IDs and function names — do NOT use ast.parse on HTML files
- Correct pre-deploy check: grep for key IDs, check HTML_LANG_COUNT=1, check DOCTYPE=1
- After deploying, verify via live site tab (Tab B)
- Check for duplicate `<html>` tags: `grep -c "<html lang" meridian.html` should return 1

### CRITICAL: Regex literals inside JS functions near backtick template literals
Never use regex literals (e.g. `/pattern/g`) inside any JS function that also contains or is near a backtick template literal string — use `.split('x').join('y')` instead. Use plain string concatenation for multi-line strings instead of template literals.

### CRITICAL: Single quotes inside single-quoted JS string literals
Never use single-quoted outer JS strings when the content contains single quotes (CSS font-family values, colour hex strings in hover handlers, etc.) — use double-quoted outer strings for all HTML-building blocks.

### CRITICAL: Inline onmouseover/onmouseout for hover states
Never use inline `onmouseover`/`onmouseout` attribute handlers for hover styling — setting `this.style.background=''` on mouseout does not reliably reset in all browsers and causes the state to stick. Always use a CSS class with `:hover` pseudo-selector instead.

### CRITICAL: Duplicate HTML bug prevention
After any patch replacing a large HTML block, always verify:
  grep -n "<!DOCTYPE\|<html lang" ~/meridian-server/meridian.html
Expected: line 1 only. Never deploy if there are two `<html lang` tags.

### tmp_ files
- tmp_*.py, tmp_*.txt, *.bak* are all gitignored
- Write scripts to ~/meridian-server/tmp_*.py, read output from tmp_*.txt
- Clean up at end of session: rm -f tmp_*.txt tmp_*.py

### Shell output keyword filter
The shell bridge swallows output containing certain words ("api", "fetch", "query string", etc.).
Workaround: write results to tmp_*.txt and read via Filesystem MCP.

---

## UI Design — Current State (Session 44)

### Colour Palette (Palette 1A)
```css
--paper: #faf8f4          /* content zone */
--paper-2: #f0ece3        /* header rows */
--paper-3: #e4dfd4        /* badges, neutral elements */
--accent: #c4783a         /* logo, AI Analysis button, amber accents */
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

### Stats panel (#info-strip) — Session 44 state
Background: `#fff`, bottom border: `2px solid #e0dbd0`
Toggled by 📊 Stats button. Health check fires on open (cached per session).

**AI Health Check row (Option C layout — Session 44):**
- Outer container: `border:1px solid rgba(0,0,0,.1); border-radius:6px; overflow:hidden`
- Header bar: `background:rgba(0,0,0,.03)` — amber dot (written by JS) + eyebrow + score (inline, 15px) left; timestamp + ↻ Refresh right
- Body: `border-left:3px solid #c4783a; padding:12px 14px` — summary + issue buttons full width
- Issue buttons use CSS class `.hc-btn` with `:hover` pseudo-selector (NOT inline onmouseover/onmouseout)
- `.hc-btn:hover` → `background:#f5f1eb; border-color:rgba(0,0,0,.1)`
- `.hc-btn:hover .hc-arrow` → `opacity:1`
- `↗ copy` arrow always visible at `opacity:.5`, goes to `1` on hover
- Clicking an issue button calls `window.sendPrompt(prompt)` which copies to clipboard + shows toast "Prompt copied — paste into Claude"
- `window.sendPrompt` is defined in the page (not injected externally)
- DOM IDs: sp-health-row, sp-health-eyebrow, sp-health-score, sp-health-summary, sp-health-issues, sp-health-ts

**Health check implementation:**
- Frontend calls `POST /api/health-check` (Flask endpoint, NOT direct Anthropic API)
- Flask uses `call_anthropic()` with server-side API key from credentials.json
- Stats payload includes: total, aiPicks, fullText, ftPct, agentRate7d, sources[], ingestion14d (14-day daily breakdown by source), zeroDaysLast7, trend (prev7avg vs last7avg per source)
- Haiku system prompt instructs analysis of daily ingestion trends, zero-days, source drop-offs, and backlog
- Bloomberg is explicitly excluded from all health check analysis — gaps are normal (manual clip source)
- `allArts` timing guard: if articles not yet loaded when Stats opens, retries up to 3× with 2s delay
- Result cached in `window._healthCache`; Refresh button forces new call
- Prompts stored in `window._hcPrompts[idx]` (index store, avoids quoting issues in onclick)
- Anthropic API account requires separate credits from claude.ai Max plan (pay-as-you-go at console.anthropic.com)

**14-day sparkline (Session 44):**
- Y-axis: fixed gridlines at multiples of 5 (0, 5, 10, 15…)
- Ceiling: actual daily max rounded UP to nearest 5 (`SPK_CEIL = Math.ceil(spkActualMax/5)*5`)
- Bars scale accurately against `SPK_CEIL` — no clipping
- Left margin `YAW=22px` for y-axis labels (#ccc, 8px)
- 3 horizontal tick lines at each multiple of 5

**Row 1** — 3 equal columns:
- Col 1: Article library headline numbers + Curation split bars
- Col 2: New articles ingestion table (24h/48h/7d/14d)
- Col 3: 14-day stacked bar sparkline with y-axis

**Row 2** — 3 equal columns: By source / Full text coverage / By topic (top 5)

**Row 3** — 4 columns: Last scraped / Unenriched backlog / 7-day rate / Agent activity

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
- Session expires periodically — manual re-login needed
- Typical cadence: 3–6 articles/day

### The Economist
- Scraper: Playwright, `economist_profile/`
- headless=False required (Cloudflare detection)
- Edition drops Tue/Thu/Sat

### Foreign Affairs
- Scraper: Playwright, `fa_profile/`
- Session: Drupal cookie valid until **2026-05-23**

### Bloomberg
- **No automated scraper — by design.** Bot detection was too strong; Playwright scraper removed.
- Articles are added manually via Chrome Extension v1.3 (clip button in logged-in session).
- Gaps in Bloomberg ingestion are NORMAL and expected — not a system fault.
- The AI health check is aware of this and will not flag Bloomberg zero-days as issues.
- Cadence depends entirely on manual clipping activity.

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
1. **Backup system** — Git tracks code but no automated DB snapshots or rollback mechanism. Need: git tag on each deploy + daily cron copy of meridian.db to dated file (keep 7 days).
2. **Full code review** — Audit server.py and meridian.html for redundant endpoints, dead code, bugs, improvement opportunities. Dedicate a full session.

### 🔴 Ingestion / Sync
3. **Economist trend decline — investigate** — Health check flagged −43% vs prior 7 days, 3 zero-days. Possible Cloudflare tightening or launchd misfire.
4. **FA trend decline — investigate** — Health check flagged −57%, 4 zero-days. May be early cookie degradation ahead of May 23 expiry.
5. **Zero ingestion Apr 6 — verify** — No FT or Economist articles on Apr 6. Check whether 11:35 sync ran and review logs.
6. **Third sync window (~17:40)** — Assess value of adding a third launchd sync. Would catch Economist late edition drops and FT afternoon pieces. Low risk to add.

### 🟡 Briefing Generator
7. **Charts not referenced in briefing body text** — Briefing prose doesn't mention embedded charts. Need chart references woven into text ("as shown in the chart below…") and a relevance check that each chart matches its section.
8. **Data points need date anchors** — Stats like "down X% YTD" need an explicit date reference (e.g. "as of 6 Apr 2026").
9. **Briefing source section — add detail grid** — Show articles per source, date range covered, and how the selection sample was drawn. Gives transparency on what the brief is based on.

### 🟡 UI / Frontend
10. **Newsletter + Suggested sections — match Feed design** — Both sections have a different visual style to the main Feed. Bring into line with card layout Option 3 (fixed date col, source·topic header, Playfair title, footer badges).
11. **Sort KT theme articles by relevance** — Detail panel currently sorts by date; should weight by keyword hit count + recency.
12. **Sub-topics filtering — implement or remove** — Filter chips render but do nothing. Decision needed.

### 🟡 Enrichment / Data
13. **FT enrichment backfill** — 32 FT articles unenriched (153/185 enriched). Run targeted backfill.
14. **pub_date normalisation stragglers** — A few old records still in `DD Month YYYY` format. One-off migration script needed.
15. **KT tag-new wiring into VPS scheduler** — Incremental tagging built, not yet hooked into sync cycle.

### 🟢 Maintenance / Watch
16. **FA cookie renewal** — Drupal cookie expires 2026-05-23. No action yet.
17. **Points of Return newsletter gap** — Latest issue is 2 Apr. Check iCloud forwarding rule.
18. **Haiku markdown fence stripping fix** — Designed in Session 43, still not deployed to VPS.
19. **Clean up tmp_*.py / tmp_*.txt files** — Periodic purge needed.

---

## Build History

### 6 April 2026 (Session 45 — Bloomberg health check fix, to-do consolidation)
- Identified that Bloomberg was being incorrectly flagged as "dead" by Haiku health check
- Bloomberg has no automated scraper by design (bot detection too strong); articles are manual-only via Chrome Extension
- Patched `/api/health-check` system prompt in server.py to explicitly exclude Bloomberg from all trend/zero-day analysis
- Updated NOTES.md Bloomberg section and Outstanding Issues with full consolidated to-do list from session review

### 5 April 2026 (Session 44 — AI health check fully operational)

**runHealthCheck SyntaxError fixed (two deploys at session start)**
- Fix 1: backtick template literal for Haiku `system:` → IIFE + plain string concatenation
- Fix 2: `.replace(/regex/)` calls in safePrompt → `.split().join()`
- Fix 3: Issue button builder rewritten with double-quoted outer strings; prompts stored in `window._hcPrompts[idx]` index store
- Second deploy fixed pre-existing `'IBM Plex Sans'` single-quote SyntaxError in button builder

**Health check API routing fixed**
- Was calling `https://api.anthropic.com/v1/messages` directly from browser (no API key, CORS blocked)
- Fixed: new `POST /api/health-check` Flask endpoint proxies call server-side with credentials.json key
- VPS credentials.json `anthropic_api_key` was empty — synced from Mac credentials.json
- Anthropic API account needed credit top-up (separate from claude.ai Max plan)
- Added friendly "credits needed" error message (HTTP 402) when account balance is zero

**Health check enriched with 14-day daily ingestion data**
- Stats payload now includes `ingestion14d` (daily totals + per-source counts), `zeroDaysLast7`, `trend` (prev7avg vs last7avg)
- Flask system prompt instructs Haiku to analyse daily trends, spot zero-days, flag drop-offs by name and date
- `allArts` timing guard added: retries up to 3× with 2s delay if articles not yet loaded on early Stats open

**Option C layout for health check row**
- Header bar: eyebrow + score inline left, timestamp + Refresh right
- Body: amber left border, summary + issues full width — no wasted score column
- `window.sendPrompt` defined in page as clipboard copy + toast ("Prompt copied — paste into Claude")
- `↗ copy` arrow always visible at opacity:.5, brightens to 1 on hover
- Hover state fixed: replaced inline `onmouseover`/`onmouseout` with CSS `.hc-btn:hover` (inline handlers caused sticky grey state)

**14-day sparkline y-axis**
- Added subtle y-axis with gridlines at multiples of 5 (0, 5, 10, 15…)
- Ceiling auto-scales to actual daily max rounded up to nearest 5
- Left margin YAW=22px for labels; bars accurately scaled, no clipping

### 5 April 2026 (Session 43 — SyntaxError diagnosed, patch designed but not applied)
- Confirmed site stuck on "Checking…" due to SyntaxError in runHealthCheck()
- Fix designed but tool call limit reached before execution

### 5 April 2026 (Session 42 — stats headings unified, AI health check panel added)
- Stats panel heading unification
- AI health check panel added (with SyntaxError bug introduced, fixed in Session 44)

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
