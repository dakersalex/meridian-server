# Meridian — Technical Notes
Last updated: 12 April 2026 (Session 49 — scraper rewrite: FT pagination, Economist Load More, FA saved+issues)

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
- ~/meridian-server/meridian.db        — Local database
- ~/meridian-server/credentials.json   — Anthropic API key
- ~/meridian-server/wake_and_sync.sh   — Mac sync + VPS push script
- ~/meridian-server/extension/         — Chrome extension v1.3
- ~/meridian-server/logs/              — Server and sync logs
- ~/meridian-server/eco_chrome_profile/ — Real Chrome profile for Economist CDP (gitignored)
- ~/meridian-server/eco_login_setup.py  — One-time Economist login helper (gitignored)
- ~/meridian-server/eco_scraper_sub.py  — Economist bookmarks subprocess scraper
- ~/meridian-server/eco_fetch_sub.py    — Economist article text fetch subprocess

## Mac Flask launchd (IMPORTANT)
- Python: /usr/bin/python3 (no venv — launchd plist runs server.py directly)
- To restart Flask safely: kill the PID on 4242 and launchd will respawn
  `lsof -ti tcp:4242 | xargs kill -9`
- NEVER rely on shell endpoint surviving a Flask kill — it dies with the process
- **CRITICAL: Mac Flask must be restarted after every deploy to load new code.**

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
Fix: always use `git reset --hard HEAD && git pull` (not `git stash && git pull`) on VPS.
TODO: add `git reset --hard HEAD` to deploy.sh before the pull step.

## Database (12 April 2026 — after Session 49)
| Source | Mac Total | Unenriched |
|---|---|---|
| Financial Times | 210 | 0 |
| The Economist | 281 | 0 |
| Foreign Affairs | 139 | ~12 (enrich_fetched running) |
| Bloomberg | ~39 | 0 |
| **Total** | **~669** | **~12** |

VPS push running at end of session — VPS will be updated shortly.

---

## Meridian Vision (decided Session 48)

A personal intelligence system that ingests FT, Economist, and Foreign Affairs via saved lists
and AI discovery, enriches every article, and distils everything into a daily briefing —
readable, audible, and scannable — for ~$11/month.

---

## API Cost Profile

**Expected: ~$0.32/day (~$11/month)**
**Current balance: $9.11 (as of Apr 12 2026)**

| Category | Model | Frequency | Est. cost/day |
|---|---|---|---|
| Web search discovery | Haiku + web_search | Morning only (gated) | ~$0.14 |
| Article enrichment | Haiku | Per new article | ~$0.03 |
| KT tag-new | Haiku | Once/day (gated) | ~$0.03 |
| Daily briefing | Sonnet | Once/day (not yet built) | ~$0.08 |
| Chat Q&A | Haiku | On demand | ~$0.04 |

### Once-per-day gates (kt_meta keys)
- `ai_pick_last_run` — gates `scrape_suggested_articles()` — morning run only
- `kt_tag_last_run` — gates `kt/tag-new` — morning run only

### Model usage by function
- `enrich_article_with_ai()` → Haiku
- `enrich_fetched_articles()` → Haiku
- `ai_pick_web_search()` → Haiku + web_search (max_attempts=3)
- `scrape_suggested_articles()` → Haiku + web_search, core 3 sources only
- `kt/tag-new` → Haiku
- `kt/seed` Call 1 → Sonnet, Call 2+3 → Haiku
- Health check → Haiku

---

## Scraper Architecture (Session 49 — COMPLETE REWRITE)

### FT Scraper
- Playwright, ft_profile/, headless=True
- **Paginates through all saved article pages** using next page button
- Stops when an **entire page** is all existing articles
- Fetches full text + enriches immediately for each new article on each page
- Navigates back to saved page after each text fetch

### Economist Scraper
- **Two subprocess scripts** (avoid Flask asyncio event loop conflict):
  - `eco_scraper_sub.py` — bookmarks scraper (headless Chrome via CDP)
  - `eco_fetch_sub.py` — article text fetcher (headless Chrome via CDP)
- Both run `--headless=new` — **no visible Chrome windows**
- `EconomistScraper.scrape()` passes `known_ids` JSON to subprocess
- Subprocess clicks **Load More** repeatedly, checks only newly revealed bottom batch
- Stops when **ALL articles in the last batch are already in DB**
- After scraping, calls `_fetch_texts()` via `eco_fetch_sub.py`
- CDP port: 9223, profile: eco_chrome_profile/
- Session renewal: `python3 ~/meridian-server/eco_login_setup.py`

### Foreign Affairs Scraper
- Playwright, fa_profile/, headless=True
- **Two sources per sync:**
  1. Saved articles page (`/my-foreign-affairs/saved-articles`) — single scroll, ~39 articles
  2. Three recent issues:
     - Mar/Apr 2026: `/issues/2026/105/2`
     - Jan/Feb 2026: `/issues/2026/105/1`
     - Nov/Dec 2025: `/issues/2025/104/6`
- **Shared `seen` set** across all sources — prevents duplicate fetches
- Article URL filter: exactly 2 path segments (`/region/slug`), slug ≥15 chars with hyphens
- Fetches text + enriches immediately for each new article
- **No pagination** — saved page and issue pages both single-scroll
- **FA cookie expires 2026-05-23** — renew before then

### pub_date Format
All pub_dates stored as ISO `YYYY-MM-DD`. Economist: extracted from URL (/YYYY/MM/DD/).

---

## Stopping Logic Summary

| Source | Page type | Stop condition |
|---|---|---|
| FT | Paginated (next button) | Entire page all existing articles |
| Economist | Load More (infinite scroll) | Last revealed batch all existing |
| FA saved | Single scroll | No stopping needed — finite page |
| FA issues | Single page | No stopping needed — ~16 articles each |

---

## Enrichment Pipeline

1. **`enrich_article_with_ai()`** — per-article Haiku call, generates summary/topic/tags
   - Only writes body if currently empty or <200 chars (never overwrites scraped body)
2. **`enrich_title_only_articles()`** — fetches full text for title_only/agent articles
   - FT: ft_profile, Economist: eco_fetch_sub.py subprocess, FA: fa_profile
3. **`enrich_fetched_articles()`** — AI enriches articles with body but no summary
4. Both 2+3 run after every sync and via `/api/enrich-title-only`

---

## Sync Architecture

### Mac → VPS (wake_and_sync.sh)
1. Playwright scrapers (FT all pages, Economist Load More, FA saved+issues)
2. Enrichment: enrich_title_only_articles() + enrich_fetched_articles()
3. Newsletter IMAP sync from iCloud
4. Push ALL articles → /api/push-articles (status IN full_text, fetched, title_only, agent)
5. Push images → /api/push-images
6. Push newsletters → /api/push-newsletters

Sync windows (Geneva time): 05:40 and 11:40.

### meridian_sync.py — DISABLED (Session 48)
Plist renamed: `com.alexdakers.meridian.sync.plist.disabled`. Never load again.

---

## DB Cleanup (Session 49)
- Deleted 21 Economist title_only articles (URLs were 404 — Economist URL changes)
- Deleted 6 Economist fetched articles with placeholder body <200 chars
- Deleted 1 FT title_only, 1 FA short-body article
- Result before FA expansion: FT=209, Eco=281, FA=64, all 0 unenriched
- FA expanded from 64 → 139 articles via issue page ingestion

---

## Curation Classification

- `auto_saved=1` = AI pick (web search agent, score ≥8)
- `auto_saved=0` = My save (saved/bookmark list or issue page)
- `auto_saved=1` is permanent — saved-list scraper never downgrades it

---

## Key Themes (KT) System
- 8 themes on VPS, Sonnet seed → Haiku assignment → Haiku key_facts
- KT lives on VPS only (Mac always empty)
- kt/tag-new: once/day gate via kt_tag_last_run

---

## Outstanding Issues / Next Steps

### 🔴 Infrastructure
1. **Backup system** — No automated DB snapshots
2. **deploy.sh git reset** — Add `git reset --hard HEAD` before pull (VPS stash poison)

### 🔴 Ingestion
3. **Economist CDP session** — Will expire eventually. Run eco_login_setup.py to renew.
4. **FA cookie renewal** — Expires 2026-05-23
5. **FA 12 unenriched** — enrich_fetched running at session end, should clear overnight
6. **Economist Load More test** — Not yet tested end-to-end with new known_ids logic. First real test will be next sync that finds new bookmarks.

### 🟡 Planned Features
7. **Daily briefing backend** — briefings table, generate_daily_briefing(), morning sync
8. **Daily briefing UI** — Read/Scan/Listen in meridian.html
9. **Chat Q&A** — Keyword retrieval, Haiku, chat UI

### 🟡 UI / Frontend
10. **Newsletter + Suggested — match Feed design**
11. **Sort KT theme articles by relevance**

---

## Build History

### 12 April 2026 (Session 49 — scraper rewrite)

**Root cause identified:** Economist scraper was crashing on startup with
`Event loop is closed!` — Flask daemon threads conflict with sync_playwright().
Fix: run all Economist CDP work in subprocess scripts with fresh Python interpreter.

**Economist subprocess architecture:**
- `eco_scraper_sub.py` — bookmarks scraper, headless, known_ids-based stop logic
- `eco_fetch_sub.py` — article text fetcher, headless, networkidle wait + multiple selectors
- Both use `--headless=new` — no visible Chrome windows
- `EconomistScraper.scrape()` passes known_ids from DB to subprocess
- Subprocess checks newly revealed batch after each Load More click
- Stops when all articles in last batch are already in DB

**FT scraper rewrite:**
- Full pagination — reads all pages not just page 1
- Stops when entire page is all existing articles
- Fetches text + enriches immediately per page

**FA scraper rewrite:**
- Two sources: saved articles + 3 recent issues (Mar/Apr 2026, Jan/Feb 2026, Nov/Dec 2025)
- Shared `seen` set prevents duplicates across sources
- URL filter: exactly 2-segment paths, slug ≥15 chars
- FA expanded from 64 → 139 articles
- No pagination (single-scroll pages)

**DB cleanup:**
- Deleted 28 unenriched articles (21 Eco 404s, 6 Eco short bodies, 1 FT, 1 FA)
- Result: FT=0, Eco=0, FA=0 unenriched before FA expansion

**Verified working:**
- FT: 1 found, 1 new on second sync ✅
- Economist: 2 found, 2 new on first sync ✅ (subprocess fix working)
- FA: 80 found, 75 new on first sync; 2 found, 2 new on second sync ✅

### 11 April 2026 (Session 48 — architecture redesign)
Full sync fixes, Economist CDP, enrichment pipeline, push query fix. VPS → 679 articles.

### Previous sessions
Session 47 — API cost reduction (Sonnet→Haiku, once-per-day gates)
Session 46 — Economist scraper overhaul, FT homepage scoring, curation classification
Session 45 — Stats panel redesign, pub_date fix, HTML dedup
Session 44 — AI health check fully operational
Session 39 — Major UI redesign, Palette 1A, card layout Option 3

---

## GitHub Visibility
- Repo: PUBLIC — github.com/dakersalex/meridian-server
- Excluded: credentials.json, cookies.json, meridian.db, newsletter_sync.py, venv/,
  tmp_*.py, tmp_*.txt, *.bak*, eco_chrome_profile/, eco_login_setup.py

## Session Starter Prompt

**Alex's opening message:**
```
Meridian session start. Read NOTES.md and run the startup sequence.
```

**Claude's startup sequence:**

### Step 1 — Load MCPs
1. `"tabs context mpc chrome"` — loads Chrome MCP
2. `"javascript tool execute page"` — loads javascript_tool
3. `"filesystem write file"` — loads Filesystem MCP

### Step 2 — Read NOTES.md
Read /Users/alexdakers/meridian-server/NOTES.md via filesystem:read_file.

### Step 3 — Set up browser tabs
Call tabs_context_mcp with createIfEmpty:true.
Tab A = localhost:8080/meridian.html (shell bridge)
Tab B = meridianreader.com/meridian.html (live verify)

### Step 4 — Inject shell bridge into Tab A
```js
window.shell = (cmd) => fetch('http://localhost:4242/api/dev/shell', {
  method:'POST', headers:{'Content-Type':'application/json'},
  body:JSON.stringify({cmd})
}).then(r=>r.json());
```

### Step 5 — Health check
Write tmp_health.py, execute via shell bridge, read tmp_hc_out.txt verbatim.
Print FULL raw output. Flag any SCRAPE FAILURE.
Last scraped uses saved_at in MILLISECONDS (divide by 1000 for fromtimestamp).
If FT or Economist show Yesterday or older AND after 07:00 Geneva → SCRAPE FAILURE.

## Autonomous Mode
Claude has full access via Filesystem MCP + shell bridge + deploy.sh.
**Claude must NEVER ask Alex to run Terminal commands.**

### Shell bridge (re-inject at start of each JS block)
```js
window.shell = (cmd) => fetch('http://localhost:4242/api/dev/shell', {
  method:'POST', headers:{'Content-Type':'application/json'},
  body:JSON.stringify({cmd})
}).then(r=>r.json());
```

### Key patterns
- Write patch scripts via filesystem:write_file → execute via window.shell()
- Always use exact text str.replace() — never line-number patches
- Shell bridge filters output containing "api", "fetch" etc — write to tmp_*.txt
- After any HTML patch, verify with grep for key element IDs
- NEVER patch VPS directly via SSH heredoc — use filesystem:write_file → shell bridge → deploy.sh
- NEVER use python3 -c for multiline scripts — write to .py file and execute
- NEVER use shell heredocs for Python containing backticks or quotes
