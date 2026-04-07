# Meridian — Technical Notes
Last updated: 7 April 2026 (Session 46 — curation model overhaul, FT homepage AI picks)

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

## Database (7 April 2026 — Mac after Session 46)
| Source | Total | Full text |
|---|---|---|
| The Economist | 306 | ~271 |
| Financial Times | 188 | ~179 |
| Foreign Affairs | 61 | 60 |
| Bloomberg | 38 | 37 |
| Other | ~19 | ~8 |
| **Total** | **~612** | **~555** |

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

## Curation Classification — IMPORTANT (revised Session 46)

`auto_saved` is the single source of truth for AI pick vs My save:
- `auto_saved=1` = AI pick — article found on source homepage, scored ≥8 by Haiku, NOT in DB at time of scrape
- `auto_saved=0` = My save — article came from user's saved/bookmark list on that source

### Core principle (decided Session 46)
**AI picks come exclusively from homepage scraping. My saves come exclusively from saved lists.**
These are fully independent pipelines. The AI never re-scores articles from saved lists.

**auto_saved=1 is permanent.** If the AI picked an article first (found on homepage, scored ≥8), it
retains auto_saved=1 forever — even if the user later saves it manually. Being saved later is
confirmation of quality, not a reclassification.

**Homepage scraper skip rule:** If a homepage candidate URL already exists in the DB (user saved it
first, or previous AI pick), skip it entirely — no DB write, no auto_saved change.

### Per-source rules
- **FT:** saved list scraper → auto_saved=0. Homepage scraper → auto_saved=1 if ≥8 and not in DB.
- **Economist:** bookmarks → auto_saved=0. Homepage → auto_saved=1 if ≥8 and not in DB. (unchanged)
- **FA:** saved articles page only — ALL auto_saved=0. No homepage scoring yet.
- **Bloomberg:** manual Chrome extension only — ALL auto_saved=0.

### What was removed (Session 46)
- `score_and_autosave_new_articles()` removed from post-sync pipeline — was retrospectively scoring
  saved-list articles and promoting them to auto_saved=1. This violated the curation model.
  The function still exists in server.py as dead code but is never called.
- FT demotion logic removed — scraper no longer flips auto_saved=1→0 when article found in saved list.
- 38 FT articles (Mac) and 43 FT articles (VPS) reset from auto_saved=1→0: none were homepage-sourced,
  all were promoted by score_and_autosave from saved list. Clean break.

### FA AI picks — future plan
To add AI picking for FA, need to:
1. Add Playwright homepage pass for foreignaffairs.com using fa_profile
2. Score visible articles with Haiku ≥8
3. Only then set auto_saved=1 for FA articles
FA homepage is JS-rendered — need Playwright, not DOM scraping.

---

## FT Homepage Scraping (added Session 46)

FT homepage is accessible logged-in via ft_profile (headless=True).
Structure: `div.headline.js-teaser-headline` contains `a[href*="/content/"]` with `<span>` title text.

**Title extraction rules:**
- Opinion cards: span text starts with "opinion content." — strip this prefix
- Section prefix cards: "The Big Read.", "Interview.", "The FT View.", "Analysis." etc — strip prefix
- Fallback: walk up to parent container and find full anchor text for the same URL

**Junk URL paths excluded:** /podcasts/, /newsletters/, /video/, /htsi/, /house-home/, /life-arts/,
/travel/, /food-drink/, /style/

**Junk title prefixes excluded:** FT quiz:, Letter:, FTAV's further reading, FT News Briefing,
Correction:, The best books, Crossword, How to spend it, Behind the Money, FT Weekend

**Scoring:** Same Haiku model, same ≥8 threshold, same interest profile as Economist homepage.
JSON fence stripping applied (same pattern as all other scoring calls).

**article_exists guard:** Uses `make_id("Financial Times", url)` = SHA1[:16] — correctly identifies
articles already in DB from saved list, preventing duplicates.

---

## Sync Architecture
### Mac → VPS (wake_and_sync.sh)
1. Playwright scrapers (FT, Economist, FA)
   - FT: reads saved list (auto_saved=0) + homepage AI picks (auto_saved=1)
   - Economist: reads bookmarks (auto_saved=0) + homepage AI picks (auto_saved=1)
   - FA: reads saved articles only (auto_saved=0)
2. AI enrichment of title-only articles (enrich_title_only_articles)
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
- Scraper: Playwright, `ft_profile/`, headless=True
- Step 1: reads myFT saved articles → auto_saved=0
- Step 2: reads FT homepage → scores with Haiku ≥8 → auto_saved=1 for new articles not in DB
- Homepage structure: `div.headline.js-teaser-headline` → `a[href*="/content/"]` → `span` title
- make_id = SHA1(source:url)[:16]

### The Economist
- Scraper: Playwright, `economist_profile/`, headless=False required (Cloudflare)
- Edition drops Tue/Thu/Sat
- pub_date: URL date is ground truth (/YYYY/MM/DD/)
- Step 1: bookmarks → auto_saved=0
- Step 2: homepage → scores with Haiku ≥8 → auto_saved=1 for new articles
- Cloudflare blocks headless — only warmed persistent profile works

### Foreign Affairs
- Scraper: Playwright, `fa_profile/`
- Session: Drupal cookie valid until **2026-05-23**
- Reads saved articles page only — ALL FA articles are My saves (auto_saved=0)
- No homepage AI scoring (yet) — see FA AI picks plan above
- FA homepage is JS-rendered, needs Playwright for scraping

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
5. **FA homepage AI scoring** — Add Playwright homepage pass using fa_profile (logged in).
   FA homepage is JS-rendered. Score with Haiku ≥8 → auto_saved=1.
   Do NOT add without homepage scraping first.
6. **Issue 2: Economist profile lock** — enrichment opens economist_profile ~90s after scraper closes it.
   Sometimes profile lock not yet released → enrichment fails silently. Options: increase sleep to 180s
   in wake_and_sync.sh (simplest), or add SingletonLock check with retry.
7. **Issue 3: Newsletter push connection reset** — batch size 67 may exceed nginx limit. Reduce to 20/batch.

### 🟡 Briefing Generator
8. **Charts not referenced in briefing prose**
9. **Data points need date anchors**
10. **Briefing source section detail grid**

### 🟡 UI / Frontend
11. **Newsletter + Suggested sections — match Feed design**
12. **Sort KT theme articles by relevance**
13. **Sub-topics filtering — implement or remove**

### 🟡 Enrichment / Data
14. **FT enrichment backfill** — Some FT articles still unenriched
15. **KT tag-new wiring into VPS scheduler**

### 🟢 Maintenance / Watch
16. **FA cookie renewal** — Drupal cookie expires 2026-05-23
17. **Points of Return newsletter gap** — Check iCloud forwarding rule
18. **Bloomberg ingestion** — Check clipping still works
19. **score_and_autosave_new_articles()** — Dead code in server.py, safe to delete in future cleanup

---

## Build History

### 7 April 2026 (Session 46 — curation model overhaul, FT homepage AI picks)

**Curation model clarified and enforced:**
- AI picks come from homepage scraping only — never from retrospective scoring of saved lists
- auto_saved=1 is permanent — AI pick status never overwritten even if user saves later
- Homepage scraper skips articles already in DB (saved first by user or previous AI pick)
- Documented as the canonical model in NOTES.md

**score_and_autosave bug fixes:**
- Markdown fence stripping added to score_and_autosave JSON parse (was silently failing)
- Raw response now logged on parse failure for diagnosis

**Pipeline changes:**
- score_and_autosave_new_articles() removed from _enrich_after_sync — no longer called post-sync
- FT demotion logic removed from FTScraper (was flipping auto_saved=1→0 for saved articles)

**Economist homepage scoring:**
- Markdown fence stripping added to Economist homepage score_text parse

**DB cleanup:**
- Mac: 38 FT articles reset auto_saved=1→0 (all were score_and_autosave promotions, not homepage picks)
- VPS: 43 FT articles reset auto_saved=1→0

**FT homepage scraping — new feature:**
- FT homepage scraped after saved-list pass within FTScraper.scrape()
- Selectors: div.headline.js-teaser-headline → a[href*="/content/"] → span text
- Opinion prefix stripping: "opinion content." stripped from span text
- Section prefix stripping: "The Big Read.", "Interview.", "The FT View.", etc.
- Junk URL/title filtering (podcasts, newsletters, lifestyle, live blogs)
- Scores with Haiku ≥8 → auto_saved=1, saves as title_only for enrichment
- article_exists() guard prevents duplicating articles already saved by user
- Committed: b023f177, deployed Mac + VPS

**Log findings (04-07 sync):**
- score_and_autosave parse failure (34 articles unscored) — root cause confirmed, fixed above
- Economist profile lock during enrichment — documented as Issue 6, not yet fixed
- Newsletter push connection reset — documented as Issue 7, not yet fixed

### 6 April 2026 (Session 45 — major bug fixes, data backfill, stats redesign)
See previous NOTES.md for full Session 45 details.

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
Tab IDs CHANGE every session — never reuse IDs from NOTES.md or memory. Always call tabs_context_mcp fresh.
Tab A = localhost:8080/meridian.html (shell bridge)
Tab B = meridianreader.com/meridian.html (live verify)

### Step 4 — Inject shell bridge into Tab A
WAIT for Step 3 tool call to return before starting this step. NEVER run in parallel with any other step.
window.shell = (cmd) => fetch('http://localhost:4242/api/dev/shell', {
  method:'POST', headers:{'Content-Type':'application/json'},
  body:JSON.stringify({cmd})
}).then(r=>r.json());
Confirm it returned "shell bridge ok" before proceeding.

### Step 5 — Health check
WAIT for Step 4 to complete before starting this step. NEVER run in parallel with Step 4.
Write tmp_health.py via filesystem:write_file, execute via shell bridge, read result via filesystem:read_text_file.
The tmp_health.py script already exists on disk from a prior session — just execute and read it.

CRITICAL — Print the FULL raw output of tmp_hc_out.txt verbatim in your response. Do NOT summarise,
paraphrase, or prettify the last scraped section. The raw ⚠️ warning flags must be visible to Alex.
If the output shows "⚠️ SCRAPE MAY HAVE MISSED" for FT or Economist, call it out explicitly at the top
of your health report — do not bury or omit it.

Last scraped uses saved_at column which is stored in MILLISECONDS (divide by 1000 for fromtimestamp).
If FT or Economist show Yesterday or older AND current time is after 07:00 Geneva → SCRAPE FAILURE.
