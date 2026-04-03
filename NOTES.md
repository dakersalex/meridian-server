# Meridian — Technical Notes
Last updated: 3 April 2026 (Session 37 — key facts UI fixes, chart backfill, backfill progress page)

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
- ~/meridian-server/backfill_progress.html — Chart backfill progress monitor page
- ~/Library/LaunchAgents/com.alexdakers.meridian.plist       — Auto-start Flask (Mac)
- ~/Library/LaunchAgents/com.alexdakers.meridian.http.plist  — Auto-start HTTP (Mac)
- ~/Library/LaunchAgents/com.alexdakers.meridian.sync.plist  — Auto-start sync (Mac)

## Mac Flask launchd (IMPORTANT)
- Python: /usr/bin/python3 (no venv — launchd plist runs server.py directly)
- To restart Flask safely: kill the PID on 4242 and launchd will respawn
  `lsof -ti tcp:4242 | xargs kill -9`
- NEVER rely on shell endpoint surviving a Flask kill — it dies with the process
- If two PIDs appear on 4242 (port conflict): kill both, launchd spawns one clean copy
- Symptom of stale process: server-error.log fills with "Port 4242 is in use"

## Daily Use
Open in browser (any device, any network):
https://meridianreader.com/meridian.html

Mac local (if needed):
http://localhost:8080/meridian.html

## VPS Management
SSH in: ssh root@204.168.179.158
Check Flask: systemctl status meridian
Restart Flask: systemctl restart meridian
Check nginx: systemctl status nginx
Restart nginx: systemctl reload nginx
View logs: cat /opt/meridian-server/meridian.log | tail -50

## Deploying Code Updates
One command from Mac (via shell bridge — Claude runs this autonomously):
  cd ~/meridian-server && ./deploy.sh "description"
(git add -A, commit, push, SSH pull on VPS, systemctl restart meridian)

## Database (3 April 2026)
- Mac: 556 articles total
- Economist: 268 articles, avg body 5,898 chars
- Financial Times: 173 articles, avg body 4,691 chars
- Foreign Affairs: 57 articles, avg body 11,470 chars
- Bloomberg: 38 articles, avg body 5,510 chars
- VPS: 534 full_text articles

---

## Autonomous Mode (Claude in Chrome + shell endpoint)

### CRITICAL: Claude must ALWAYS run commands autonomously
Claude has full access to run all terminal commands, patches, and deployments via:
- **Filesystem MCP** — write patch scripts to ~/meridian-server/
- **Shell bridge** — execute via window.shell() in Tab A (localhost)
- **deploy.sh** — commit, push and deploy to VPS in one command

**Claude must NEVER ask Alex to run commands in Terminal.** This includes:
- Running patch scripts (filesystem:write_file → window.shell('python3 ~/meridian-server/tmp_*.py'))
- Syntax checks (window.shell('python3 -m py_compile ~/meridian-server/server.py'))
- Deploying (window.shell('cd ~/meridian-server && ./deploy.sh "message"'))
- SSH/VPS commands (write script locally → scp to VPS → ssh to run it)
- Checking logs (fetch via shell bridge → write to ~/meridian-server/tmp_*.txt → read via Filesystem MCP)

Alex is not present during execution. Complete all tasks end-to-end autonomously.

### Shell bridge (re-inject at start of each JS block)
```js
window.shell = (cmd) => fetch('http://localhost:4242/api/dev/shell', {
  method:'POST', headers:{'Content-Type':'application/json'},
  body:JSON.stringify({cmd})
}).then(r=>r.json());
```

### MCP setup
- Filesystem MCP: read/write ~/meridian-server/
- Claude in Chrome MCP: browser tab control
- Tab A (localhost:8080/meridian.html): shell bridge
- Tab B (meridianreader.com/meridian.html): live site verification
- TabIds change every session — always call tabs_context_mcp first

### NEVER restart Flask via shell endpoint — kills itself mid-request

### Key patterns
- Write patch scripts via filesystem:write_file → execute via window.shell()
- VPS operations: write script locally → scp to VPS → ssh to run it
- Shell endpoint filters some keywords — write output to ~/meridian-server/tmp_*.txt, read via Filesystem MCP
- Line-number patches are DANGEROUS — always use str.replace(OLD, NEW) with exact text
- Always python3 -m py_compile server.py before deploying
- After deploying, verify via live site tab (Tab B)
- Tmp files: always clean up with git rm tmp_*.py tmp_*.txt after sessions
- ft_profile / economist_profile / fa_profile are used by launchd sync — never run Playwright
  against them while sync service is active (profile lock causes 0-char results)

### Dangerous operations checklist
Before any DELETE/UPDATE on DB: SELECT preview first, confirm what will be affected, then execute.

---

## Article Body Text — Architecture (IMPORTANT)

### Correct architecture (enforced from Session 36)
- `body` = raw scraped article text from Playwright (5,000–20,000 chars for full articles)
- `summary` = 2-3 sentence AI summary (Haiku) — used for Feed card previews + keyword matching
- `status = 'full_text'` = body was successfully populated from Playwright

### The fullSummary overwrite bug — FIXED
- **Root cause**: `enrich_article_with_ai` was always overwriting `body` with AI `fullSummary`
  (~2,000 chars), even when Playwright had already stored real article text (5,000+ chars)
- **Fix deployed (Session 36)**: `enrich_article_with_ai` now only writes to `body` if body
  is currently empty (<200 chars). Raw scraped text is always preserved

### Re-enrichment completed
- Economist: 266 articles re-enriched — avg 2,132 → 5,898 chars ✅
- FA: 57 articles re-enriched — avg 2,500 → 11,469 chars ✅
- FT: 38 articles still need re-enrichment — will self-correct on next sync

---

## Source-Specific Notes

### Financial Times
- Scraper: Playwright, `ft_profile/`, saved articles page + article text fetch
- Selector (updated Session 36): `div.n-content-body p` (primary — FT changed CSS classes)
  fallback: `div[class*='n-content-body'] p`, `div[class*='article__content'] p`
- Session: expires periodically, requires manual re-login to ft_profile Chromium
  Symptom: Playwright returns "Just a moment..." (Cloudflare) with 0 paragraphs
- 38 FT articles have AI summaries as body — will be fixed on next sync

### The Economist
- Scraper: Playwright, `economist_profile/`, bookmarks + homepage agent picks
- Selector: `p[data-component="paragraph"]` — confirmed working
- headless=False required (Cloudflare detection)
- Re-enrichment done — avg body 5,898 chars

### Foreign Affairs
- Scraper: Playwright, `fa_profile/`, saved articles page
- TWO page templates — both now handled:
  - New template: `div.article__body-content p`
  - Old template: `section.rich-text p` (added Session 36)
- Session: Drupal cookie `SSESS8d72...` valid until 2026-05-23
- 56/57 articles full text, avg 11,469 chars

### Bloomberg
- NO automated scraper — Bloomberg bot detection kills headless Playwright
- All 38 Bloomberg articles added via Chrome Extension v1.3 clip button
- Workflow: open Bloomberg article in Chrome → click Meridian extension → "Clip Article"

### Bloomberg Chrome Extension (extension/ folder)
- Clip Article: scrapes current page DOM, sends to /api/articles (works for any source)
- Sync Bookmarks: bulk import from FT/Economist saved pages (NOT Bloomberg)

---

## Feed Source Restriction (Session 36)

Only FT/Economist/FA/Bloomberg articles are auto-saved to the main Feed (auto_saved=1).
All other sources remain in Suggested only. Current Feed: 64 auto-saved articles.

Implemented in server.py:
- `FEED_CORE_SOURCES = {'Financial Times', 'The Economist', 'Foreign Affairs', 'Bloomberg'}`
- `run_agent()` skips non-core sources — they stay in Suggested with status='new'

---

## Key Themes (KT) System

### Current state (3 April 2026)
- 8 themes on VPS, sorted by article count descending
- key_facts: ✅ FULLY POPULATED — 10 facts per theme across all 8 themes
- Seeded at 558 articles; last seeded timestamp 1775121120868

### Theme grid (Session 37)
- kt-fact-top: padding 2px 12px 6px, height 68px, flex-start, gap 1px, overflow hidden
- kt-fact-title: no margin-top (removed auto — was causing bottom-anchoring)
- All 10 key fact cards uniform height, number+title top-aligned

### kt/seed pipeline
- Call 1: Sonnet, 165 sample titles → 8 themes. max_tokens=3000, timeout=60s
- Call 2: Haiku, batches of 50 → article→theme assignments
- Call 3: Haiku per theme → key_facts + subtopic_details. max_tokens=2500, timeout=45s

---

## Briefing Generator Tab

New third tab alongside News Feed and Key Themes.
All three modes work: All themes / Select a theme / Focused topic.

---

## Chart/Image System

### Current state (3 April 2026) — BACKFILL COMPLETE
- **163 images (charts + maps) across 89 Economist articles** — this is the ceiling
- **Backfill ran Session 37**: all 173 remaining articles processed, 0 new images found
- **Confirmed via log**: no auth/paywall errors — articles loaded cleanly, just no chart figures
- The 173 articles with 0 images are text-only pieces (news, opinion, analysis)
  The 89 articles with images are data-heavy pieces (economics, finance, trade data)
- **Do not re-run backfill on existing articles** — exhaustively confirmed no more available
- New articles will get charts captured automatically during enrichment going forward
- Charts only appear in downloaded PDF briefs (Full Intelligence Brief), not modal text

### /api/images/recent endpoint (added Session 37)
- Returns last N images as base64 for monitoring
- Uses sqlite3.connect(DB_PATH) directly (NOT get_db() — that helper doesn't exist)
- Query params: limit (default 20), every_nth (default 5)

### Backfill progress page
- File: ~/meridian-server/backfill_progress.html
- Access: http://localhost:8080/backfill_progress.html
- Shows: articles done, images captured, total in DB, ETA, every 5th image preview
- Polls /api/images/backfill/status and /api/images/recent every 5s

---

## Intelligence Brief Pipeline (✅ WORKING)

- brief_pdf.py — ReportLab + Pillow, A4 PDF
- Single Sonnet call: text used for both modal and PDF
- Full brief: charts embedded; Short brief: text only
- Temporal bucketing: 4 buckets × 15 articles, full_text first, per-source cap 5

---

## Service Worker
- sw.js cache version: meridian-v5
- nginx: no-cache for meridian.html and sw.js

## Schedule (Geneva/CEST)
- 05:40 / 11:40 — Mac syncs FT + Economist + FA via Playwright
- 05:50 / 11:50 — VPS scores, agent auto-saves 8+ to Feed (core sources only)

---

## Next Steps (priority order)

1. **Clean up tmp_ files** — many accumulated this session. Run:
   git rm --ignore-unmatch tmp_*.py tmp_*.txt tmp_*.png && git commit -m "chore: remove tmp files"

2. **FT 38 short articles** — will self-correct on next scheduled sync (05:40/11:40).
   New FT selector deployed. enrich fix deployed. No manual action needed.

3. **Sort theme articles by relevance** — detail panel shows most recent first; sort by
   keyword hit count + summary length.

4. **Sub-topics filtering** — chips do nothing; decide implement or remove.

5. **Checking server retry loop** — frontend shows "Checking server" during ~8-10s Flask
   restart on every deploy. Add JS retry loop (every 3s, up to 30s).

6. **FA session renewal** — Drupal cookie expires 2026-05-23. Before that date, open
   fa_profile Chromium and log in to foreignaffairs.com.

7. **Focused Intelligence Briefing** — Briefing Generator "Focused topic" mode. Test quality.

8. **ft_profile lock** — launchd sync owns ft_profile. Safe window for manual Playwright:
   outside 05:35-06:00 and 11:35-12:00.

---

## Build History

### 3 April 2026 (Session 37 — key facts UI, chart backfill)

**Key fact card UI fixes**
- Fixed `margin-top: auto` on `.kt-fact-title` — was anchoring titles to bottom of box
- `.kt-fact-top`: padding 2px 12px 6px, height 68px fixed, justify-content flex-start, gap 1px
- All 10 cards now uniform height with number+title top-aligned immediately under each other

**Chart backfill — completed and exhausted**
- Ran backfill against all 173 Economist articles with no images
- Result: 0 new images. Confirmed via log — no errors, no paywall hits
- Articles loaded cleanly; they are genuinely text-only pieces
- 163 images / 89 articles is confirmed ceiling for current corpus
- Do not re-run backfill on existing articles

**New API route: /api/images/recent**
- Returns last N images as base64 (sqlite3.connect(DB_PATH) pattern)
- Used by backfill progress monitor page

**Backfill progress page: backfill_progress.html**
- Live stats + image previews, polls every 5s
- Access at http://localhost:8080/backfill_progress.html

**Mac Flask restart pattern clarified**
- No venv — launchd runs /usr/bin/python3 server.py directly
- Kill PID on 4242 → launchd auto-respawns with latest code
- Port conflict (two PIDs): kill both → launchd spawns one clean copy

### 3 April 2026 (Session 36 — article health, body text fixes, feed cleanup)
- enrich_article_with_ai fullSummary overwrite bug fixed
- Economist + FA re-enrichment complete
- FT selector updated, Feed source restriction added
- Briefing Generator tab JS SyntaxError fixed
- getThemeArticles() signature fix
- 534 articles pushed to VPS

### 2 April 2026 (Session 35)
- FA selector fix, Economist VPS backfill
- Key Themes crash fix, permanent/manual theme grid
- Tmp cleanup

### 1 April 2026 (Sessions 29-34)
- Brief PDF pipeline, chart processing
- KT system, seeding, key_facts
- Article filtering improvements

---

## GitHub Visibility
- Repo: PUBLIC — github.com/dakersalex/meridian-server
- Excluded: credentials.json, cookies.json, meridian.db, newsletter_sync.py, venv/

## Session Starter Prompt
---
You are helping me build Meridian, my personal news aggregator. Please read my technical notes from the Filesystem MCP at /Users/alexdakers/meridian-server/NOTES.md and review them. Then run the session start health check.
---

Note for Claude: Read NOTES.md via Filesystem MCP (NOT GitHub URL — blocked).
NEVER ask Alex to run Terminal commands — run everything autonomously via shell bridge.
Never restart Flask via the shell endpoint.
