# Meridian — Technical Notes
Last updated: 12 April 2026 (Session 49 — scraper rewrite + stats panel fixes)

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

## Mac Flask launchd
- To restart: `lsof -ti tcp:4242 | xargs kill -9`
- CRITICAL: Mac Flask must be restarted after every deploy

## Daily Use
https://meridianreader.com/meridian.html

## Deploying Code Updates
  cd ~/meridian-server && ./deploy.sh "description"

## Database (12 April 2026 — end of Session 49)
| Source | VPS Total | Status |
|---|---|---|
| Financial Times | 217 | 100% full_text |
| The Economist | 281 | 100% full_text |
| Foreign Affairs | 138 | 100% full_text |
| Bloomberg | 39 | 97% full_text |
| Other | 46 | — |
| **Total** | **721** | **100% FT/Eco/FA** |

API balance: $9.11 (Apr 12) — ~28 days runway at $0.32/day

---

## Scraper Architecture (Session 49 — COMPLETE REWRITE)

### FT Scraper
- Playwright, ft_profile/, headless=True
- Paginates through ALL saved article pages (next button)
- Stops when entire page is all existing articles
- Fetches text + enriches immediately per new article

### Economist Scraper
- Two subprocess scripts — avoids Flask asyncio event loop conflict:
  - `eco_scraper_sub.py` — bookmarks scraper (headless Chrome `--headless=new`)
  - `eco_fetch_sub.py` — article text fetcher (headless Chrome `--headless=new`)
- No visible Chrome windows
- Passes `known_ids` JSON to subprocess
- Clicks Load More until last revealed batch ALL already in DB
- CDP port: 9223, profile: eco_chrome_profile/
- Session renewal: `python3 ~/meridian-server/eco_login_setup.py`

### Foreign Affairs Scraper
- Playwright, fa_profile/, headless=True
- Two sources per sync:
  1. Saved articles: `/my-foreign-affairs/saved-articles` — single scroll, ~39 articles
  2. Three recent issues:
     - Mar/Apr 2026: `/issues/2026/105/2`
     - Jan/Feb 2026: `/issues/2026/105/1`
     - Nov/Dec 2025: `/issues/2025/104/6`
- Shared `seen` set across all sources — prevents duplicates
- URL filter: exactly 2 path segments, slug ≥15 chars with hyphens
- FA cookie expires 2026-05-23 — renew before then

### Stopping Logic
| Source | Stop condition |
|---|---|
| FT | Entire page all existing articles |
| Economist | Last Load More batch all existing |
| FA saved | No stopping — finite single page |
| FA issues | No stopping — ~16 articles each |

---

## Stats Panel — Last Scraped
- Reads from `kt_meta` keys: `last_sync_ft`, `last_sync_economist`, `last_sync_fa`
- Written by `run_sync()` on every successful completion (regardless of new articles found)
- Exposed via `/api/sync/last-run` endpoint
- Bloomberg excluded (manual-only, no scraper)
- CRITICAL: stats panel uses async IIFE for the fetch — do not use bare `await` in non-async context

## Stats Panel — Health Check
- Collapsed by default — body hidden until button clicked
- Button: "Run health check" (was "Refresh")
- No auto-run on panel open — manual only
- Uses Haiku, ~$0.003 per call
- Button uses polling wrapper to wait for `window.runHealthCheck` to be defined

## Sync Architecture

### Mac → VPS (wake_and_sync.sh)
1. Scrape (FT all pages, Economist Load More, FA saved+issues)
2. Enrich: enrich_title_only_articles() + enrich_fetched_articles()
3. Newsletter IMAP sync
4. Push articles, images, newsletters to VPS
Sync windows (Geneva): 05:40 and 11:40

### kt_meta last_sync keys
Seeds on VPS: `last_sync_ft`, `last_sync_economist`, `last_sync_fa` = '2026-04-12T10:41:xx'
These update automatically after every successful run_sync() call going forward.

---

## Enrichment Pipeline
1. `enrich_article_with_ai()` — per-article Haiku, generates summary/topic/tags
2. `enrich_title_only_articles()` — fetches text for title_only/agent articles
3. `enrich_fetched_articles()` — AI enriches articles with body but no summary
4. Both 2+3 run after every sync and via `/api/enrich-title-only`

---

## API Cost Profile (~$0.32/day)
- enrich_article_with_ai → Haiku
- health check → Haiku, ~$0.003/call, manual-only
- scrape_suggested → Haiku + web_search, morning only (gated)
- ai_pick_web_search → Haiku + web_search, morning only (gated)

---

## Outstanding Issues / Next Steps

### 🔴 Must fix soon
1. FA cookie renewal — expires 2026-05-23
2. Economist CDP session — will expire eventually (run eco_login_setup.py)

### 🟡 Planned Features
3. Daily briefing backend — briefings table, Sonnet, morning sync
4. Daily briefing UI — Read/Scan/Listen
5. Chat Q&A — keyword retrieval, Haiku

### 🟡 Known minor issues
6. FT 1 pending — "North Sea rethink" article, unfetchable, ignore
7. Swim lanes show pub_date not saved_at — correct behaviour, reflects publication dates
8. Bloomberg unenriched 1 — manual-only, nothing to do

---

## Build History

### 12 April 2026 (Session 49)

**Scraper rewrites:**
- FT: full pagination, stops on all-existing page
- Economist: subprocess architecture (headless, event loop fix), Load More with known_ids
- FA: saved articles + 3 recent issues, shared seen set, 2-segment URL filter
- FA expanded: 64 → 138 articles
- All sources at 0 unenriched

**Stats panel fixes:**
- Last Scraped: now uses kt_meta `last_sync_*` timestamps from run_sync()
- Last Scraped: Bloomberg excluded (manual-only)
- Health check: collapsed by default, manual "Run health check" button
- Health check: fixed await-in-non-async bug that crashed page JS
- Fixed `fetched` status articles — bulk-updated to `full_text` on Mac + VPS

**DB cleanup:**
- Deleted 28 stale/broken articles (21 Eco 404s, 6 Eco short bodies, 1 FT, 1 FA)
- Deleted remaining paywall-truncated FA stubs from VPS

### 11 April 2026 (Session 48)
Full sync fixes, Economist CDP, enrichment pipeline, push query fix.

---

## Autonomous Mode
Claude has full access via Filesystem MCP + shell bridge + deploy.sh.
NEVER ask Alex to run Terminal commands.

### Shell bridge
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
- NEVER use bare `await` in non-async JS context — wrap in async IIFE
- NEVER patch VPS directly via SSH heredoc
- NEVER use python3 -c for multiline scripts

### Session startup
1. Load MCPs: tabs_context_mcp, javascript_tool, filesystem write_file
2. Read NOTES.md
3. Set up Tab A (localhost:8080) + Tab B (meridianreader.com)
4. Inject shell bridge into Tab A
5. Run health check script
