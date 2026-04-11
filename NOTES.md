# Meridian — Technical Notes
Last updated: 11 April 2026 (Session 48 — architecture redesign, Economist CDP scraper, sync fixes)

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
- ~/meridian-server/eco_chrome_profile/ — Real Chrome profile for Economist CDP scraper (gitignored)
- ~/meridian-server/eco_login_setup.py  — One-time Economist login helper (gitignored)

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

## Database (11 April 2026 — VPS, after Session 48 push)
| Source | Total |
|---|---|
| The Economist | 306 |
| Financial Times | 214 |
| Foreign Affairs | 74 |
| Bloomberg | 39 |
| Other (suggested) | 46 |
| **VPS Total** | **679** |

Mac local DB: ~630 articles. VPS is canonical.
Full text coverage: ~94%. Unenriched: ~87 (pending API credit top-up).

---

## Meridian Vision & Architecture (decided Session 48)

### What Meridian is for
A personal intelligence system that ingests FT, Economist, and Foreign Affairs via saved lists
and AI discovery, enriches every article with AI, and distils everything into a daily briefing
— readable, audible, and scannable — so you stay informed without reading dozens of articles.

### Target API budget: ~$20/month
Estimated actual: ~$11/month (see cost model below)

---

## API Cost Profile (Session 48 revised)

**Expected daily cost: ~$0.32/day (~$11/month recurring)**

| Category | Model | Frequency | Est. cost/day |
|---|---|---|---|
| Web search discovery | Haiku + web_search | Morning only (gated) | ~$0.14 |
| Article enrichment | Haiku | Per new article (~5/day avg) | ~$0.03 |
| KT tag-new | Haiku | Once/day (gated) | ~$0.03 |
| Daily briefing | Sonnet | Once/day (morning, not yet built) | ~$0.08 |
| Chat Q&A | Haiku | On demand (~5 questions/day) | ~$0.04 |

On-demand: KT seed (~2×/month) + Brief PDF (~4×/month) ≈ $1.50/month extra.

### Once-per-day gates (kt_meta keys)
- `ai_pick_last_run` — gates `scrape_suggested_articles()` — set on first morning run
- `kt_tag_last_run` — gates `kt/tag-new` — set after first tag run each day
Both use `datetime.now().strftime('%Y-%m-%d')` as the value. Reset automatically at midnight.

### Model usage by function
- `enrich_article_with_ai()` → Haiku
- `ai_pick_web_search()` → Haiku + web_search (max_attempts=3)
- `scrape_suggested_articles()` → Haiku + web_search (max_attempts=3), core 3 sources only
- `kt/tag-new` → Haiku
- `kt/seed` Call 1 (theme gen) → Sonnet
- `kt/seed` Call 2 (assignment) → Haiku
- `kt/seed` Call 3 (key_facts) → Haiku
- Briefing generator → Sonnet
- Health check → Haiku
- Chat Q&A (planned) → Haiku, smart keyword retrieval of top 20 articles by relevance

---

## pub_date Format
All pub_dates stored as ISO `YYYY-MM-DD`.
`normalize_pub_date()` in server.py handles incoming formats.

### Economist pub_date policy (decided Session 45)
URL date is ground truth for Economist. URL dates (/YYYY/MM/DD/) are the online publication date.
The bookmark page shows print edition dates (1-3 days later) — these are NOT used.

### FA pub_date
Use whichever date is shown on the actual article page.

---

## Curation Classification

`auto_saved` is the single source of truth for AI pick vs My save:
- `auto_saved=1` = AI pick — found via web search agent, scored ≥8
- `auto_saved=0` = My save — came from saved/bookmark list on that source

**auto_saved=1 is permanent.** The saved-list scraper never downgrades auto_saved.

### Per-source rules (Session 48)
- **FT:** saved list → auto_saved=0. Web search agent ≥8 → auto_saved=1.
  FT homepage Playwright scoring pass REMOVED (Session 48).
- **Economist:** bookmarks → auto_saved=0. Web search agent ≥8 → auto_saved=1.
  CDP scraper now active (see below).
- **FA:** saved articles page only — ALL auto_saved=0. No homepage scoring.
- **Bloomberg:** manual Chrome extension only — ALL auto_saved=0.

---

## Economist Scraper — CDP Architecture (Session 48)

### Status: ACTIVE — uses real Chrome via CDP
Playwright Chromium was blocked by Cloudflare (HTTP 403, "Just a moment...").
Real Chrome (Google Chrome.app) bypasses Cloudflare completely — confirmed in testing.

### How it works
1. `EconomistScraper.scrape()` launches Google Chrome with `--remote-debugging-port=9223`
   and `--user-data-dir=eco_chrome_profile/`
2. Playwright connects via `connect_over_cdp('http://localhost:9223')`
3. Navigates to `/for-you/bookmarks`, scrapes titles and URLs
4. Chrome process terminated after scrape completes
5. `eco_chrome_profile/` is gitignored — session persists locally only

### Session management
- `eco_chrome_profile/` stores the authenticated Economist session
- Session will eventually expire — to renew: `python3 ~/meridian-server/eco_login_setup.py`
  (opens Chrome to Economist login, saves session to profile)
- CDP port: 9223 (avoids conflict with any other debugging sessions)
- SingletonLock cleared automatically before each launch

### Scraper logic (unchanged from Session 45/46)
- Navigates to `/for-you/bookmarks` — newest-saved first
- Scopes to `<main>` to avoid nav/header date links
- Early exit: stops after 3 consecutive existing articles
- Title extraction: anchor text inside h3/h2, headline class, anchor text, URL slug fallback
- Junk filters: /podcasts/, /newsletters/, /events/, Espresso, World in Brief, etc.
- All articles: auto_saved=0 (My saves)

### Cloudflare notes (for reference)
- Playwright Chromium: HTTP 403 immediately — TLS fingerprint detected
- Real Chrome: passes completely — genuine browser fingerprint
- eco_chrome_profile cookies NOT transferable from economist_profile (macOS Keychain encryption)

---

## FT Scraper — Current State (Session 48)

### Two-pass → single-pass (simplified)
FT homepage Playwright scoring pass REMOVED in Session 48.
FT scraper now reads saved list only (myFT → auto_saved=0).
Discovery of new FT articles now handled entirely by web search agent.

---

## AI Picks — web_search architecture (Session 48)

### ai_pick_web_search() — core 3 sources only
- Model: Haiku + web_search tool
- max_attempts: 3
- Two topic passes: geopolitics/energy + macroeconomics/finance
- Sources: economist.com, ft.com, foreignaffairs.com ONLY (bloomberg removed)
- score ≥8 → articles table, auto_saved=1 (Feed)
- score 6-7 → suggested_articles table
- Runs morning sync only (gated by ai_pick_last_run)

### scrape_suggested_articles() — core 3 sources only
- Model: Haiku + web_search tool
- max_attempts: 3
- Sources: Economist, FT, Foreign Affairs ONLY (external sources removed in Session 48)
- All results → suggested_articles table
- Once-per-day gate via kt_meta `ai_pick_last_run`

---

## Sync Architecture (Session 48)

### Mac → VPS (wake_and_sync.sh)
1. Playwright scrapers (FT saved list, Economist CDP, FA saved list)
2. AI enrichment of new articles (Haiku, per article)
3. Newsletter IMAP sync from iCloud
4. Push ALL articles → /api/push-articles (ALL statuses: full_text, fetched, title_only, agent)
5. Push images → /api/push-images
6. Push newsletters → /api/push-newsletters
7. Push interviews → /api/push-interviews

Sync windows (Geneva time): 05:40 and 11:40.
Web search agent: morning only (gated, never runs at 11:40).

### meridian_sync.py — DISABLED (Session 48)
- Was producing 415 errors for 16+ days — completely broken and redundant
- Launchd plist renamed: `com.alexdakers.meridian.sync.plist.disabled`
- File kept but never loaded. wake_and_sync.sh is the only sync mechanism.

### Push query — ALL statuses (fixed Session 48)
Previously only pushed `status = 'full_text'` — 62 articles were stuck on Mac.
Now pushes `status IN ('full_text', 'fetched', 'title_only', 'agent')`.
First push after fix: 638 articles pushed (up from 568), VPS jumped to 679 total.

### score_and_autosave_new_articles() — FULLY REMOVED (Session 48)
- Function deleted from server.py (~120 lines)
- Call removed from VPS push_articles() handler (was firing on every push, costing API money)
- Tombstone comment left at removal point

---

## Planned Features (next sessions)

### Daily Briefing (Phase 3-4 — next session)
- Auto-generated each morning after enrichment completes
- Sonnet reads last 24-48h articles + KT theme summaries
- Outputs: (1) prose narrative 3-5 min read, (2) 5 key story cards, (3) audio script
- Stored in `briefings` DB table as JSON
- UI: Read / Scan / Listen modes. Browser Web Speech API for audio (free).
- Distinct from PDF brief — lightweight daily catch-up vs deep formal output

### Chat Q&A (Phase 5 — future session)
- Simple chat input in UI
- Backend: keyword-match question → top 20 most relevant articles → full body to Haiku
- No vector DB — SQLite keyword scoring
- Haiku responds with article citations
- Cost: ~$0.03-0.05 per question

---

## Autonomous Mode
Claude has full access to run all terminal commands, patches, and deployments via:
- **Filesystem MCP** — write patch scripts to ~/meridian-server/
- **Shell bridge** — execute via window.shell() in Tab A (localhost)
- **deploy.sh** — commit, push and deploy to VPS in one command

**Claude must NEVER ask Alex to run Terminal commands.**
**Exception: interactive scripts (e.g. eco_login_setup.py) use osascript to open Terminal.**

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
- Interactive scripts needing user input: use osascript to open Terminal window

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
- Reads myFT saved articles only → auto_saved=0
- FT homepage scoring pass removed in Session 48
- make_id = SHA1(source:url)[:16]

### The Economist
- Scraper: **ACTIVE** — real Chrome via CDP (eco_chrome_profile/, port 9223)
- Session renewal: `python3 ~/meridian-server/eco_login_setup.py`
- pub_date: URL date is ground truth (/YYYY/MM/DD/)
- All bookmarks → auto_saved=0

### Foreign Affairs
- Scraper: Playwright, `fa_profile/`
- Session: Drupal cookie valid until **2026-05-23**
- Reads saved articles page only — ALL FA articles are My saves (auto_saved=0)

### Bloomberg
- Manual Chrome extension clip only — all My saves (auto_saved=0)
- Bloomberg excluded from all health check analysis
- Bloomberg removed from web search agent trusted domains (Session 48)

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
3. **Anthropic API credits** — Top up to enable article enrichment backlog (~87 unenriched)

### 🔴 Ingestion / Sync
4. **Economist CDP session expiry** — Will eventually expire. Run `eco_login_setup.py` to renew.
5. **FA cookie renewal** — Drupal cookie expires 2026-05-23
6. **Newsletter push connection reset** — Reduce batch size from 67 to 20/batch

### 🟡 Planned Features (in order)
7. **Daily briefing backend** — briefings table, generate_daily_briefing() Sonnet, wire into morning sync
8. **Daily briefing UI** — Read / Scan / Listen modes in meridian.html
9. **Chat Q&A** — Keyword retrieval, Haiku over top 20 full-body articles, chat UI panel

### 🟡 Briefing Generator (existing PDF)
10. **Charts not referenced in briefing prose**
11. **Data points need date anchors**

### 🟡 UI / Frontend
12. **Newsletter + Suggested sections — match Feed design**
13. **Sort KT theme articles by relevance**
14. **Sub-topics filtering — implement or remove**

### 🟡 Enrichment / Data
15. **FT enrichment backfill** — Some FT articles still unenriched
16. **Gemini Flash fallback** — Free tier fallback when Anthropic credits exhausted

---

## Build History

### 11 April 2026 (Session 48 — architecture redesign + sync fixes)

**Context:** Full architecture review. VPS was stale (5-7 days behind) due to two bugs:
push query only included `full_text` articles, and `meridian_sync.py` had been broken
(415 errors) for 16 days. Conducted full product design session to clarify vision and simplify.

**Architecture decisions:**
- Meridian vision: personal intelligence system — ingest, enrich, distil into daily briefing
- Ingestion: FT saved list + FA saved list + Economist bookmarks (CDP) + web search discovery
- AI discovery: core 3 sources only (FT, Economist, FA) — external sources removed
- Sync: keep 05:40 + 11:40 Geneva, web search morning only, meridian_sync.py disabled
- New features planned: daily briefing (Read/Scan/Listen), Chat Q&A (smart keyword retrieval)
- Target budget: ~$11/month vs $20 budget

**Code changes deployed:**

1. **Economist scraper rewritten — CDP instead of Playwright Chromium**
   - Playwright Chromium blocked by Cloudflare (HTTP 403 confirmed in test)
   - Real Chrome (Google Chrome.app) bypasses Cloudflare — confirmed working
   - EconomistScraper.scrape() now launches Chrome on port 9223, connects via CDP
   - eco_chrome_profile/ stores session (gitignored)
   - eco_login_setup.py for session renewal (gitignored)

2. **wake_and_sync.sh push query fixed**
   - Changed from `WHERE status = 'full_text'` to `WHERE status IN ('full_text', 'fetched', 'title_only', 'agent')`
   - Immediate push: 638 articles pushed, VPS total 679 (up from 659)

3. **meridian_sync.py disabled**
   - Launchd plist renamed `.disabled`, process unloaded
   - Was producing 415 errors for 16 days — completely redundant

4. **score_and_autosave_new_articles() removed**
   - Function deleted from server.py (~120 lines)
   - Call removed from push_articles() VPS handler

5. **scrape_suggested_articles() — external sources removed**
   - Prompt now instructs: core 3 sources only (Economist, FT, Foreign Affairs)
   - Removed: Brookings, RAND, Atlantic Council, CFR, Foreign Policy, major newspapers

6. **ai_pick_web_search() — Bloomberg removed from trusted domains**
   - Bloomberg is manual-only; no value in web-searching for it

7. **eco_chrome_profile removed from git**
   - Was accidentally committed (740MB of Chrome binary data)
   - Removed with `git rm -r --cached`, gitignore updated

### 11 April 2026 (Session 47 — API cost reduction)
See previous session notes for full details. Key: Sonnet→Haiku for web search,
once-per-day gates, max_attempts 6→3. Cost reduced from ~$3.30/day to ~$0.31/day.

### Previous sessions
Session 46 — Economist scraper overhaul, FT homepage scoring, curation classification
Session 45 — Stats panel redesign, pub_date fix, HTML dedup
Session 44 — AI health check fully operational
Session 43 — SyntaxError diagnosed
Session 42 — Stats headings, health check panel added
Session 39 — Major UI redesign, Palette 1A, card layout Option 3
Session 38 — Newsletter + interview VPS sync, Bloomberg filter

---

## GitHub Visibility
- Repo: PUBLIC — github.com/dakersalex/meridian-server
- Excluded: credentials.json, cookies.json, meridian.db, newsletter_sync.py, venv/,
  tmp_*.py, tmp_*.txt, *.bak*, eco_chrome_profile/, eco_login_setup.py

## Session Starter Prompt

**Alex's opening message (copy this exactly):**
```
Meridian session start. Read NOTES.md and run the startup sequence.
```

**Claude's startup sequence (defined here so NOTES.md is the single source of truth):**

### Step 1 — Load MCPs
Call tool_search with EXACTLY these queries in order:
1. `"tabs context mcp chrome"` — loads Chrome MCP
2. `"javascript tool execute page"` — loads javascript_tool
3. `"filesystem write file"` — loads Filesystem MCP

### Step 2 — Read NOTES.md
Read /Users/alexdakers/meridian-server/NOTES.md via filesystem:read_file.

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
