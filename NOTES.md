# Meridian — Technical Notes
Last updated: 7 April 2026 (Session 46 continued — Economist scraper overhaul)

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

Note: 8 Economist bookmarks confirmed missing from DB (scraper bug, now fixed).
They will be picked up at next successful sync.

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

**auto_saved=1 is permanent.** If the AI picked an article first, it retains auto_saved=1 even if
the user later saves it manually. The saved-list scraper never downgrades auto_saved.

**Homepage scraper skip rule:** If a homepage candidate URL already exists in the DB, skip it entirely.

### Per-source rules
- **FT:** saved list → auto_saved=0. Homepage → auto_saved=1 if ≥8 and not in DB.
- **Economist:** bookmarks → auto_saved=0. Homepage → auto_saved=1 if ≥8 and not in DB.
- **FA:** saved articles page only — ALL auto_saved=0. No homepage scoring yet.
- **Bloomberg:** manual Chrome extension only — ALL auto_saved=0.

### What was removed (Session 46)
- `score_and_autosave_new_articles()` removed from post-sync pipeline
- FT demotion logic removed
- 38 FT (Mac) and 43 FT (VPS) articles reset from auto_saved=1→0

---

## FT Homepage Scraping (added Session 46)

FT homepage accessible logged-in via ft_profile (headless=True).
Structure: `div.headline.js-teaser-headline` → `a[href*="/content/"]` → `<span>` title text.

**Title extraction:**
- Opinion cards: strip "opinion content." prefix from span text
- Section prefix cards: strip "The Big Read.", "Interview.", "The FT View.", "Analysis." etc.

**Junk filters:** /podcasts/, /newsletters/, /video/, /htsi/, /house-home/, /life-arts/, etc.

**Scoring:** Haiku ≥8 → auto_saved=1. JSON fence stripping applied. article_exists() guard prevents dupes.

---

## Economist Scraper — Current State (Session 46, commit 296818ea)

### Bookmark pass (Step 1)
- Opens economist_profile (headless=False — required for Cloudflare)
- Navigates to /for-you/bookmarks
- Bookmark page order: **newest-saved first**
- **Selector: scope to `<main>` with nav-stripping fallback**
  - `_main = soup.find("main") or soup`
  - Check if `<main>` contains date links; if not (JS-rendered), strip `nav/header` elements first
  - CRITICAL: The "For You" nav contains Feed / Topics / Bookmarks tab links with date URLs.
    These appear earlier in the DOM than bookmark cards and corrupt iteration order if not excluded.
- Early exit: stops after 3 CONSECUTIVE existing articles (not 1). Counter resets on any new article.

### Cloudflare behaviour
- The economist_profile normally passes Cloudflare (warm persistent session, headless=False)
- Repeated rapid sync attempts within a session cause Cloudflare to challenge the profile
- After Cloudflare challenges, the profile needs ~30-60 min to recover
- Scheduled syncs (05:35, 11:35) work reliably because there's a long gap between attempts
- Do NOT trigger multiple manual syncs in quick succession — it poisons the session
- **Root cause of Apr 7 Cloudflare issues:** Step 2 homepage was the trigger. Multiple rapid
  manual retries after the initial challenge made it unrecoverable for the session.
  Topics page is authenticated → far less bot-detectable.

### SingletonLock fix
- `_clear_stale_profile_lock(profile_dir)` called before every economist_profile launch (5 sites)
- Removes stale lock if no Chrome process owns the profile — prevents ProcessSingleton errors

### Topics pass (Step 2) — SINGLE BROWSER, commit 296818ea
- Replaced homepage entirely with `/for-you/topics` (personalised, authenticated)
- Random 3-6s pause between bookmark navigation and Topics navigation (shorter, less risk)
- **Extraction method: `__next_f` JSON parsing, not HTML scraping**
  - The Topics page is Next.js SSR — article cards are NOT in the rendered HTML
  - Article data is embedded in `self.__next_f.push([1, "..."])` script tags as inline JSON
  - Data block keyed as `2f:{"data":[...]}` — parsed directly from `page.content()`
  - Each topic entry contains 4 articles with full metadata: url, headline, date_published, is_saved
  - Podcasts filtered out (identity=="podcast")
  - Articles already in DB skipped via `article_exists()`
- Topics page shows articles from topics you follow (e.g. Geopolitics, AI, Economy, War in Middle East)
- Scored by Haiku ≥8 → auto_saved=1; topic name stored in article's topic field
- No Haiku scoring was needed on homepage before; now it's even better — pre-filtered by interest

---

## Sync Architecture
### Mac → VPS (wake_and_sync.sh)
1. Playwright scrapers (FT, Economist, FA)
   - FT: reads saved list (auto_saved=0) + homepage AI picks (auto_saved=1)
   - Economist: reads bookmarks (auto_saved=0) + homepage AI picks (auto_saved=1)
   - FA: reads saved articles only (auto_saved=0)
2. AI enrichment of title-only articles
3. Newsletter IMAP sync from iCloud
4. Push articles → /api/push-articles
5. Push images → /api/push-images
6. Push newsletters → /api/push-newsletters
7. Push interviews → /api/push-interviews

Sync windows (Geneva time): 05:35 and 11:35.

### CRITICAL: Push script must include title_only articles
The push script must include `status IN ('full_text','title_only','fetched','agent')`.

### meridian_sync.py — 415 bug (fixed Session 45)
`requests.post('/api/sync')` had no Content-Type — Flask returned 415. Fix: added `json={}`.

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
- For file-to-file patches: write OLD and NEW to separate .txt files, read both in patch script
  This avoids Python string escaping issues with quotes and regex characters.

### CRITICAL: Regex literals inside JS functions near backtick template literals
Use `.split('x').join('y')` instead of regex literals.

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
Col 1: Library — Total/My saves/AI picks/Full text with right-aligned %
Col 2: Swim lanes — LANE_H=40, LANE_GAP=20, HTML div, hover tooltips, shared scale
Col 3: 14 Day Total — 3 swim-lane bars, AI% adjacent, summary below

**Row 2** — 3 equal columns: By source / Full text coverage / By topic
**Row 3** — 4 columns: Last scraped / Unenriched backlog / 7-day rate / Agent activity

**AI Health Check (top of Stats panel):**
- Bloomberg excluded from all health check analysis
- max_tokens: 1800, DOM IDs: sp-health-row, sp-health-score, sp-health-summary, sp-health-issues

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
- Step 2: reads FT homepage → scores Haiku ≥8 → auto_saved=1 for new articles not in DB
- Homepage structure: `div.headline.js-teaser-headline` → `a[href*="/content/"]` → `<span>` title
- make_id = SHA1(source:url)[:16]

### The Economist
- Scraper: Playwright, `economist_profile/`, headless=False required (Cloudflare)
- Edition drops Tue/Thu/Sat
- pub_date: URL date is ground truth (/YYYY/MM/DD/)
- Step 1: bookmarks — scope to `<main>`, 3-consecutive early exit, auto_saved=0
- Step 2: homepage — same browser session, 8-15s random pause, Haiku ≥8 → auto_saved=1
- SingletonLock cleared before all 5 economist_profile launch sites

### Foreign Affairs
- Scraper: Playwright, `fa_profile/`
- Session: Drupal cookie valid until **2026-05-23**
- Reads saved articles page only — ALL FA articles are My saves (auto_saved=0)
- No homepage AI scoring yet

### Bloomberg
- Manual Chrome extension clip only — all My saves (auto_saved=0)
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

### 🔴 Ingestion / Sync
3. **8 missing Economist bookmarks** — Will be picked up at next successful sync (fixes deployed)
4. **Third sync window (~17:40)** — Easy addition to launchd
5. **FA homepage AI scoring** — Add Playwright homepage pass using fa_profile
6. ~~**Economist homepage scoring**~~ — **DONE (commit 296818ea):** Replaced with /for-you/topics
   authenticated JSON extraction. No more homepage visits, no Cloudflare risk from Step 2.
7. **Newsletter push connection reset** — Reduce batch size from 67 to 20/batch

### 🟡 Briefing Generator
8. **Charts not referenced in briefing prose**
9. **Data points need date anchors**

### 🟡 UI / Frontend
10. **Newsletter + Suggested sections — match Feed design**
11. **Sort KT theme articles by relevance**
12. **Sub-topics filtering — implement or remove**

### 🟡 Enrichment / Data
13. **FT enrichment backfill** — Some FT articles still unenriched
14. **KT tag-new wiring into VPS scheduler**

### 🟢 Maintenance / Watch
15. **FA cookie renewal** — Drupal cookie expires 2026-05-23
16. **Bloomberg ingestion** — Check clipping still works
17. **score_and_autosave_new_articles()** — Dead code in server.py, safe to delete

---

## Build History

### 7 April 2026 (Session 46 continued — Economist scraper overhaul)

**Economist bookmark scraper — three root cause fixes:**

1. **Wrong selector scope (commit 7442f5b4 + c410a6de):**
   - BUG: `soup.select("a[href*='/20']")` scanned entire HTML document
   - The For You nav (Feed / Topics / Bookmarks tabs) contains dated article links that appear
     earlier in the DOM than the actual bookmark cards, corrupting iteration order entirely
   - FIX: scope to `<main>` first; if `<main>` empty (JS-rendered), strip nav/header elements
   - Bookmark page order is newest-saved first — new bookmarks ARE at the top visually,
     but nav DOM links were being processed before them

2. **Aggressive early-exit (commit 8ebb4ffa):**
   - BUG: stopped at the FIRST existing article, never looking further
   - FIX: stop after 3 CONSECUTIVE existing articles, counter resets on any new article
   - Same pattern as ForeignAffairsScraper which had always used 3-consecutive

**Confirmed missing bookmarks:** Audit against Alex's bookmark page showed 8/29 articles missing.
All 8 were new bookmarks (newest-saved, at top of page) missed due to the selector scope bug.
Will be ingested at next successful Economist sync.

**Cloudflare session poisoning:** Multiple manual sync attempts during Session 46 caused Cloudflare
to challenge the economist_profile session. Profile needs ~30-60 min to recover. Scheduled syncs
(05:35, 11:35) are reliable because they run with a long gap.

**Fresh-context homepage experiment (abandoned):**
Attempted to run homepage pass in a separate non-persistent browser (different Cloudflare fingerprint).
Abandoned because sync_playwright() cannot be nested within an existing playwright context.
Reverted to single-browser approach with random 8-15s pause. Commit f3ec3037.

**SingletonLock fix (commit fbd77cde):**
`_clear_stale_profile_lock()` helper added, called before all 5 economist_profile launch sites.
Prevents ProcessSingleton errors from stale locks after unexpected Chrome exits.

**score_and_autosave fixes:**
- Markdown fence stripping added (commit 64a60f20)
- Removed from post-sync pipeline entirely (commit 30a60674)

**FT homepage AI picks (commit b023f177):**
Full homepage scraping pass added to FTScraper — first genuine FT AI picks from homepage.

### 6 April 2026 (Session 45)
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
1. `"javascript tool navigate tabs"` — loads Chrome MCP
2. `"filesystem write file"` — loads Filesystem MCP

### Step 2 — Read NOTES.md
Read /Users/alexdakers/meridian-server/NOTES.md via filesystem:read_text_file.

### Step 3 — Set up browser tabs
Call tabs_context_mcp with createIfEmpty:true to get current tab IDs.
Tab IDs CHANGE every session — never reuse IDs from NOTES.md or memory.
Tab A = localhost:8080/meridian.html (shell bridge)
Tab B = meridianreader.com/meridian.html (live verify)

### Step 4 — Inject shell bridge into Tab A
window.shell = (cmd) => fetch('http://localhost:4242/api/dev/shell', {
  method:'POST', headers:{'Content-Type':'application/json'},
  body:JSON.stringify({cmd})
}).then(r=>r.json());
Confirm it returned "shell bridge ok" before proceeding.

### Step 5 — Health check
Write tmp_health.py via filesystem:write_file, execute via shell bridge, read result.

CRITICAL — Print the FULL raw output of tmp_hc_out.txt verbatim. Do NOT summarise.
If output shows "⚠️ SCRAPE MAY HAVE MISSED" for FT or Economist, call it out explicitly.

Last scraped uses saved_at in MILLISECONDS (divide by 1000 for fromtimestamp).
If FT or Economist show Yesterday or older AND current time is after 07:00 Geneva → SCRAPE FAILURE.
