# Meridian — Technical Notes
Last updated: 11 April 2026 (Session 48 — architecture redesign, CDP scraper, sync + enrichment fixes)

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
- ~/meridian-server/meridian.db        — Local database (not synced to VPS)
- ~/meridian-server/credentials.json   — Anthropic API key
- ~/meridian-server/cookies.json       — Publication session cookies
- ~/meridian-server/brief_pdf.py       — Intelligence brief PDF generation module
- ~/meridian-server/newsletter_sync.py — iCloud IMAP newsletter poller
- ~/meridian-server/wake_and_sync.sh   — Mac sync + VPS push script
- ~/meridian-server/extension/         — Chrome extension v1.3
- ~/meridian-server/logs/              — Server and sync logs
- ~/meridian-server/eco_chrome_profile/ — Real Chrome profile for Economist CDP (gitignored)
- ~/meridian-server/eco_login_setup.py  — One-time Economist login helper (gitignored)

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

## Database (11 April 2026 — after Session 48)
| Source | VPS Total |
|---|---|
| The Economist | 306 |
| Financial Times | 214 |
| Foreign Affairs | 74 |
| Bloomberg | 39 |
| Other | 46 |
| **Total** | **679** |

Mac local: ~630. VPS is canonical.
Unenriched (Mac): 33 remaining after backfill (27 Economist title_only awaiting CDP fetch,
3 FA too-short body, 2 FT edge cases, 1 Bloomberg paywall).

---

## Meridian Vision (decided Session 48)

A personal intelligence system that ingests FT, Economist, and Foreign Affairs via saved lists
and AI discovery, enriches every article, and distils everything into a daily briefing —
readable, audible, and scannable — for ~$11/month.

---

## API Cost Profile

**Expected: ~$0.32/day (~$11/month)**

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
- `enrich_fetched_articles()` → Haiku (new — pipeline gap fix)
- `ai_pick_web_search()` → Haiku + web_search (max_attempts=3)
- `scrape_suggested_articles()` → Haiku + web_search, core 3 sources only
- `kt/tag-new` → Haiku
- `kt/seed` Call 1 → Sonnet, Call 2+3 → Haiku
- Briefing generator → Sonnet
- Health check → Haiku
- Chat Q&A (planned) → Haiku, keyword retrieval top 20 articles

---

## pub_date Format
All pub_dates stored as ISO `YYYY-MM-DD`. `normalize_pub_date()` handles incoming formats.

### Economist pub_date policy
URL date is ground truth (/YYYY/MM/DD/). Bookmark page shows print edition dates — NOT used.

---

## Curation Classification

- `auto_saved=1` = AI pick (web search agent, score ≥8)
- `auto_saved=0` = My save (saved/bookmark list)
- `auto_saved=1` is permanent — saved-list scraper never downgrades it

### Per-source rules (Session 48)
- **FT:** saved list → auto_saved=0. Web search agent ≥8 → auto_saved=1.
  FT homepage Playwright scoring REMOVED Session 48.
- **Economist:** bookmarks → auto_saved=0. Web search agent ≥8 → auto_saved=1.
- **FA:** saved articles page only → auto_saved=0.
- **Bloomberg:** manual Chrome extension only → auto_saved=0.

---

## Economist Scraper — CDP Architecture (Session 48)

### Status: ACTIVE — real Chrome via CDP
Playwright Chromium was Cloudflare blocked (HTTP 403). Real Chrome bypasses it.

### How it works
1. `EconomistScraper.scrape()` launches Google Chrome on port 9223 with `eco_chrome_profile/`
2. Playwright connects via `connect_over_cdp('http://localhost:9223')`
3. Navigates to `/for-you/bookmarks`, scrapes bookmark articles
4. Chrome terminated after scrape
5. `eco_chrome_profile/` gitignored — session persists locally

### Session renewal
- When session expires: `python3 ~/meridian-server/eco_login_setup.py`
  (opens Chrome, you log in, session saved to eco_chrome_profile/)
- CDP port: 9223. Startup wait: 5s (increased from 3s in Session 48 to prevent ECONNREFUSED)

### Scraper logic
- Navigates to `/for-you/bookmarks` — newest-saved first
- Scopes to `<main>` to avoid nav date links
- Early exit: stops after 3 consecutive existing articles
- Junk filters: /podcasts/, /newsletters/, /events/, Espresso, World in Brief, etc.
- All bookmarks: auto_saved=0

### Also used in enrich_title_only_articles()
The Economist block in `enrich_title_only_articles()` also uses CDP (same port/profile).
5s startup wait also applied there.

---

## FT Scraper (Session 48)
- Playwright, `ft_profile/`, headless=True
- Reads myFT saved list only → auto_saved=0
- FT homepage scoring pass REMOVED Session 48
- Discovery via web search agent only

---

## AI Picks — web_search (Session 48)

### ai_pick_web_search()
- Haiku + web_search, max_attempts=3
- Two passes: geopolitics/energy + macroeconomics/finance
- Sources: economist.com, ft.com, foreignaffairs.com ONLY
- score ≥8 → Feed (auto_saved=1), score 6-7 → Suggested
- Morning sync only (gated by ai_pick_last_run)

### scrape_suggested_articles()
- Haiku + web_search, max_attempts=3
- Sources: Economist, FT, Foreign Affairs ONLY (external sources removed Session 48)
- All → suggested_articles table
- Once-per-day gate via ai_pick_last_run

---

## Sync Architecture (Session 48)

### Mac → VPS (wake_and_sync.sh)
1. Playwright scrapers (FT saved list, Economist CDP, FA saved list)
2. Enrichment: enrich_title_only_articles() + enrich_fetched_articles()
3. Newsletter IMAP sync from iCloud
4. Push ALL articles → /api/push-articles (status IN full_text, fetched, title_only, agent)
5. Push images → /api/push-images
6. Push newsletters → /api/push-newsletters
7. Push interviews → /api/push-interviews

Sync windows (Geneva time): 05:40 and 11:40.
Web search agent: morning only (gated).

### meridian_sync.py — DISABLED (Session 48)
Plist renamed: `com.alexdakers.meridian.sync.plist.disabled`. Never load again.

### Push query — all statuses (fixed Session 48)
`WHERE status IN ('full_text', 'fetched', 'title_only', 'agent')`

---

## Enrichment Pipeline (Session 48)

Three functions now cover all cases:

1. **`enrich_title_only_articles()`** — fetches full text AND enriches `title_only`/`agent` articles
   - FT: ft_profile Playwright
   - Economist: eco_chrome_profile CDP (5s wait)
   - FA: fa_profile Playwright
   - Bloomberg: bloomberg_profile Playwright
   - Other: generic urllib scrape

2. **`enrich_fetched_articles()`** — NEW Session 48
   - Handles `full_text`/`fetched` articles that have body but no summary
   - Closes pipeline gap where articles got text but missed AI enrichment call
   - Called after enrich_title_only_articles() in both sync and /api/enrich-title-only

3. **`enrich_article_with_ai()`** — per-article Haiku call
   - Generates summary, topic, tags in one call
   - Only writes body if currently empty or <200 chars

Both 1 and 2 are wired into:
- `_enrich_after_sync()` (runs after every scrape)
- `/api/enrich-title-only` route (manual trigger)

---

## Planned Features (next sessions)

### Daily Briefing (Phase 3-4)
- Auto-generated each morning after enrichment
- Sonnet reads last 24-48h articles + KT themes
- Outputs: prose (3-5 min), 5 key story cards, audio script
- Stored in `briefings` DB table
- UI: Read / Scan / Listen (browser Web Speech API)

### Chat Q&A (Phase 5)
- Keyword-match question → top 20 articles → full body to Haiku
- Haiku responds with article citations
- ~$0.03-0.05 per question

---

## Autonomous Mode
Claude has full access via Filesystem MCP + shell bridge + deploy.sh.
**Claude must NEVER ask Alex to run Terminal commands.**
**Exception: interactive scripts use osascript to open Terminal.**

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

### Key patterns
- Write patch scripts via filesystem:write_file → execute via window.shell()
- Always use exact text str.replace() — never line-number patches
- Pre-deploy check: `grep -c "<html lang" meridian.html` must return 1
- Shell bridge filters output containing "api", "fetch" etc — write to tmp_*.txt
- After any HTML patch, verify with grep for key element IDs
- Interactive scripts needing user input: use osascript to open Terminal

### CRITICAL: Regex literals inside JS functions near backtick template literals
Use `.split('x').join('y')` instead of regex literals.

### tmp_ files
All gitignored. Clean up at end of session: `rm -f tmp_*.txt tmp_*.py`

---

## UI Design — Current State (Session 45)

### Colour Palette (Palette 1A)
```css
--paper: #faf8f4; --paper-2: #f0ece3; --paper-3: #e4dfd4;
--accent: #c4783a; --ink: #1a1a1a; --green: #2d6b45; --rule: rgba(0,0,0,0.1)
```

### Stats Panel
Row 1: Library (150px) | Swim lanes (1fr) | 14 Day Total (1fr)
Row 2: By source | Full text coverage | By topic
Row 3: Last scraped | Unenriched backlog | 7-day rate | Agent activity
AI Health Check at top — Bloomberg excluded, max_tokens 1800

### Article card (Option 3)
[date 44px] | [source·topic | ✕] / [title Playfair] / [summary] / [badges·tags]

---

## Source-Specific Notes

### Financial Times
- Playwright, ft_profile/, headless=True, saved list only → auto_saved=0

### The Economist
- CDP, eco_chrome_profile/, port 9223, 5s startup wait
- Session renewal: `python3 ~/meridian-server/eco_login_setup.py`
- pub_date: URL date ground truth

### Foreign Affairs
- Playwright, fa_profile/
- **Drupal cookie expires 2026-05-23** — renew before then
- Saved articles only → auto_saved=0

### Bloomberg
- Manual Chrome extension only → auto_saved=0
- Excluded from health check analysis

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
5. **27 Economist title_only** — Need CDP text fetch (will happen on next sync)
6. **Newsletter push connection reset** — Reduce batch size 67 → 20

### 🟡 Planned Features
7. **Daily briefing backend** — briefings table, generate_daily_briefing(), morning sync
8. **Daily briefing UI** — Read/Scan/Listen in meridian.html
9. **Chat Q&A** — Keyword retrieval, Haiku, chat UI

### 🟡 Briefing Generator (PDF)
10. **Charts not referenced in prose**
11. **Data points need date anchors**

### 🟡 UI / Frontend
12. **Newsletter + Suggested — match Feed design**
13. **Sort KT theme articles by relevance**
14. **Sub-topics filtering — implement or remove**

### 🟡 Enrichment / Data
15. **3 FA articles with <300 char body** — paywall truncation, may need manual clip
16. **Gemini Flash fallback** — Free fallback when Anthropic credits exhausted

---

## Build History

### 11 April 2026 (Session 48 — full architecture redesign)

**Phase 1 — Sync fixes:**
- wake_and_sync.sh: push query now includes ALL statuses (was full_text only)
- meridian_sync.py disabled (16 days of 415 errors, completely redundant)
- First full push: 638 articles → VPS jumped to 679

**Phase 2 — server.py cleanup:**
- score_and_autosave_new_articles() removed entirely (~120 lines)
- Removed from VPS push_articles() handler
- FT homepage Playwright scoring pass removed
- scrape_suggested: external sources removed, core 3 only
- ai_pick_web_search: bloomberg removed from trusted domains

**Phase 3 — Economist CDP scraper:**
- Playwright Cloudflare block confirmed (HTTP 403)
- Real Chrome via CDP confirmed working (bookmarks loaded, 10 articles visible)
- EconomistScraper.scrape() rewritten to use eco_chrome_profile/ on port 9223
- eco_chrome_profile/ gitignored (was accidentally committed — cleaned up)
- eco_login_setup.py for session renewal

**Phase 4 — Enrichment pipeline fixes:**
- enrich_title_only_articles() Economist block: replaced _clear_stale_profile_lock
  (NameError) with CDP approach — was crashing entire enrichment function
- CDP startup wait increased 3s → 5s (prevent ECONNREFUSED)
- enrich_fetched_articles() added — new function covering full_text/fetched articles
  with body but no summary (pipeline gap that left 42 FT/FA articles unenriched)
- Both functions wired into _enrich_after_sync() and /api/enrich-title-only
- Backfill run: 50 articles enriched, 0 failed
- Unenriched count: 87 → 33 (27 remaining are Economist title_only awaiting CDP fetch)

**Architecture decisions:**
- Ingestion: FT saved + FA saved + Economist CDP + web search discovery (core 3 only)
- Daily briefing planned: Sonnet, auto-generated morning, Read/Scan/Listen UI
- Chat Q&A planned: keyword retrieval, top 20 articles full body, Haiku
- Budget: ~$11/month vs $20 target

### 11 April 2026 (Session 47 — API cost reduction)
Sonnet→Haiku for web search. Once-per-day gates. max_attempts 6→3.
Cost: $3.30/day → $0.31/day.

### Previous sessions
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
Print FULL raw output. Flag any ⚠️ SCRAPE MAY HAVE MISSED.
Last scraped uses saved_at in MILLISECONDS (divide by 1000 for fromtimestamp).
If FT or Economist show Yesterday or older AND after 07:00 Geneva → SCRAPE FAILURE.
