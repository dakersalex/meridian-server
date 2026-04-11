# Meridian — Technical Notes
Last updated: 11 April 2026 (Session 47 — API cost reduction)

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
- **CRITICAL: Mac Flask must be restarted after every deploy to load new code.**
  `deploy.sh` restarts Flask on VPS automatically, but NOT on Mac. The Mac process
  keeps running old in-memory code until killed. Always kill after Mac-side patches.

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

## Database (11 April 2026 — Mac, Session 47)
| Source | Total | AI picks | Manual |
|---|---|---|---|
| The Economist | 306 | 17 | 289 |
| Financial Times | 198 | 1 | 197 |
| Foreign Affairs | 64 | 3 | 61 |
| Bloomberg | 38 | 0 | 38 |
| **Total** | **625** | **~21** | **~604** |

Full text coverage: 579/625 (92%). Unenriched (no summary): 46.
VPS is the canonical DB. Mac local DB may differ slightly.

---

## API Cost Profile (after Session 47 optimisations)

**Expected daily cost: ~$0.31/day** (down from ~$3.30/day before this session)

| Category | Model | Frequency | Est. cost/day |
|---|---|---|---|
| AI pick web search | Haiku + web_search | Once/day (morning sync only) | ~$0.08 |
| scrape_suggested external loop | Haiku + web_search | Once/day (gated) | ~$0.05 |
| Web search tool fees | — | ~6 calls/day max | ~$0.10 |
| Article enrichment | Haiku | Per new article | ~$0.05 |
| kt/tag-new | Haiku | Once/day (gated) | ~$0.03 |
| KT seed (manual only) | Sonnet + Haiku | On demand | ~$0.33 per run |

### Once-per-day gates (kt_meta keys)
- `ai_pick_last_run` — gates `scrape_suggested_articles()` — set on first morning run
- `kt_tag_last_run` — gates `kt/tag-new` — set after first tag run each day
Both use `datetime.now().strftime('%Y-%m-%d')` as the value. Reset automatically at midnight.

### Model usage by function
- `enrich_article_with_ai()` → Haiku
- `ai_pick_web_search()` → Haiku + web_search (max_attempts=3)
- `scrape_suggested_articles()` agentic loop → Haiku + web_search (max_attempts=3)
- `kt/tag-new` → Haiku
- `kt/seed` Call 1 (theme gen) → Sonnet
- `kt/seed` Call 2 (assignment) → Haiku
- `kt/seed` Call 3 (key_facts) → Haiku
- Briefing generator → Sonnet
- Health check → Haiku

### Saved article scrapers — zero API cost unless new articles found
FT and FA Playwright scrapers only call the API to enrich newly found articles.
With no new saves, they cost nothing. Economist scraper intentionally disabled (see below).

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

## Economist Scraper — Current State

### Status: INTENTIONALLY DISABLED (return [] in scrape())
Cloudflare reliably blocks the economist_profile on repeated attempts.
Decision (Session 47): leave disabled, clip Economist articles manually via Chrome extension.
Do NOT attempt to re-enable without a Cloudflare mitigation strategy.

### When it was working — bookmark pass design
- Opens economist_profile (headless=False — required for Cloudflare)
- Navigates to /for-you/bookmarks
- Bookmark page order: **newest-saved first**
- Scopes to `<main>` with nav-stripping fallback to avoid For You nav date links
- Early exit: stops after 3 CONSECUTIVE existing articles

### Cloudflare notes
- Repeated rapid sync attempts within a session poison the profile (needs 30-60 min recovery)
- Scheduled syncs work reliably because of the long gap between runs
- Do NOT trigger multiple manual syncs in quick succession

### SingletonLock fix
- `_clear_stale_profile_lock(profile_dir)` called before every economist_profile launch
- Prevents ProcessSingleton errors from stale locks after unexpected Chrome exits

---

## AI Picks — web_search architecture (Session 46/47)

### ai_pick_web_search() — trusted sources
- Model: Haiku + web_search tool
- max_attempts: 3 (reduced from 6 in Session 47)
- Two search passes: geopolitics/war/energy + macroeconomics/finance
- Sources: Economist, FT, Foreign Affairs, Bloomberg only
- score ≥8 → articles table, auto_saved=1 (Feed)
- score 6-7 → suggested_articles table

### scrape_suggested_articles() — external sources
- Model: Haiku + web_search tool
- max_attempts: 3
- Sources: FA, Foreign Policy, Brookings, RAND, Atlantic Council, CFR, etc.
- All results → suggested_articles table
- Once-per-day gate via kt_meta `ai_pick_last_run`

---

## Sync Architecture
### Mac → VPS (wake_and_sync.sh)
1. Playwright scrapers (FT, Economist disabled, FA)
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
- Tab B (meridianreader.com/meridian.html): live verify
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
- Scraper: **DISABLED** (`return []` in scrape()) — Cloudflare blocks reliably
- Manual clip via Chrome extension only
- pub_date: URL date is ground truth (/YYYY/MM/DD/)

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
- `kt/tag-new` runs once per day maximum (gated via kt_meta `kt_tag_last_run`)

---

## Outstanding Issues / Next Steps

### 🔴 Infrastructure / Stability
1. **Backup system** — No automated DB snapshots
2. **deploy.sh — add git reset --hard HEAD** before pull to prevent VPS stash poisoning
3. **Anthropic API credits** — Depleted as of ~Apr 9. Top up before next session.
   After top-up: 3 FA articles will auto-enrich on next sync (Trump's Iran Gamble etc.)

### 🔴 Ingestion / Sync
4. **Third sync window (~17:40)** — Easy addition to launchd
5. **FA homepage AI scoring** — Add Playwright homepage pass using fa_profile
6. **Newsletter push connection reset** — Reduce batch size from 67 to 20/batch

### 🟡 Briefing Generator
7. **Charts not referenced in briefing prose**
8. **Data points need date anchors**

### 🟡 UI / Frontend
9. **Newsletter + Suggested sections — match Feed design**
10. **Sort KT theme articles by relevance**
11. **Sub-topics filtering — implement or remove**

### 🟡 Enrichment / Data
12. **FT enrichment backfill** — Some FT articles still unenriched
13. **Gemini Flash fallback** — Use free Gemini Flash for enrichment when Anthropic credits exhausted
    (Google AI Studio key, free tier 1500 req/day — enough for normal operation)

### 🟢 Maintenance / Watch
14. **FA cookie renewal** — Drupal cookie expires 2026-05-23
15. **Bloomberg ingestion** — Check clipping still works
16. **score_and_autosave_new_articles()** — Dead code in server.py, safe to delete

---

## Build History

### 11 April 2026 (Session 47 — API cost reduction)

**Context:** Anthropic API credits exhausted (~Apr 9). Root cause: `scrape_suggested_articles()`
was running two Sonnet 4.6 agentic web search loops twice daily (~$3.30/day total).

**Cost analysis from CSV (Apr 1–8):**
- Total spend: ~$28 over 8 days (~$3.30/day avg)
- Apr 7 spike: $6.97 (multiple manual syncs during Session 46 each triggered full Sonnet loops)
- Sonnet 4.6 was 64% of all spend
- Web search tool fees: ~$0.40/day

**Fixes deployed (commits 08318cfc + a971853b):**

1. **ai_pick_web_search(): Sonnet → Haiku** (commit 08318cfc)
   - All 4 call sites in scrape_suggested_articles() switched from claude-sonnet-4-6 to claude-haiku-4-5-20251001
   - Applies to: main agentic loop, pub_date lookup, scoring call 1, fallback scoring

2. **Once-per-day gate on scrape_suggested_articles()** (commit 08318cfc)
   - Checks kt_meta key `ai_pick_last_run` against today's date
   - 11:35 sync now skips AI pick web search entirely if morning sync already ran

3. **web_search max_attempts: 6 → 3** (commit a971853b)
   - `_run_agentic_search()` default reduced from 6 to 3 attempts
   - Cuts web search tool fees ~50%

4. **Once-per-day gate on kt/tag-new** (commit a971853b)
   - Checks kt_meta key `kt_tag_last_run` against today's date
   - Returns immediately if already ran today

**Revised daily cost: ~$0.31/day** (down from ~$3.30/day)
**$20 top-up should now last ~2 months**

**Scraper status confirmed this session:**
- FT: working, finds 0 new articles (all 50 saved-list cards already in DB — not a bug)
- Economist: disabled intentionally, `return []` in place — Cloudflare blocks consistently
- FA: working, finds 0 new articles (all 36 already in DB)
- `_clear_stale_profile_lock` NameError: fixed by Flask restart this session

### 7 April 2026 (Session 46 continued — Economist scraper overhaul)
See previous NOTES.md for full Session 46 details.

### Previous sessions
Session 45 — Stats panel redesign, pub_date fix, HTML dedup
Session 44 — AI health check fully operational
Session 43 — SyntaxError diagnosed
Session 42 — stats headings, health check panel added
Session 41 — stats panel redesign
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
1. `"tabs context mcp chrome"` — loads Chrome MCP (use this query, not "javascript tool navigate tabs")
2. `"javascript tool execute page"` — loads javascript_tool
3. `"filesystem write file"` — loads Filesystem MCP

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
Confirm it returns a valid response before proceeding.

### Step 5 — Health check
Write tmp_health.py via filesystem:write_file, execute via shell bridge, read result.

CRITICAL — Print the FULL raw output of tmp_hc_out.txt verbatim. Do NOT summarise.
If output shows "⚠️ SCRAPE MAY HAVE MISSED" for FT or Economist, call it out explicitly.

Last scraped uses saved_at in MILLISECONDS (divide by 1000 for fromtimestamp).
If FT or Economist show Yesterday or older AND current time is after 07:00 Geneva → SCRAPE FAILURE.
