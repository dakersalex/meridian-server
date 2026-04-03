# Meridian — Technical Notes
Last updated: 3 April 2026 (Session 36 — article health check, body text fixes, feed cleanup)

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
- ~/Library/LaunchAgents/com.alexdakers.meridian.plist       — Auto-start Flask (Mac)
- ~/Library/LaunchAgents/com.alexdakers.meridian.http.plist  — Auto-start HTTP (Mac)
- ~/Library/LaunchAgents/com.alexdakers.meridian.sync.plist  — Auto-start sync (Mac)

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
- Mac: 554 articles total
- Economist: 268 articles, avg body 5,898 chars (real text — fixed this session)
- Financial Times: 173 articles, avg body 3,837 chars (38 still AI summaries — see FT below)
- Foreign Affairs: 57 articles, avg body 11,469 chars (56/57 full text — fixed)
- Bloomberg: 38 articles, all manual clips via Chrome extension
- VPS: 534 full_text articles pushed (backfill complete)

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
- **Why it happened**: `enrich_article_with_ai` was written before Playwright scrapers existed
  (Sessions 1-3). When scrapers were added later, the overwrite was never removed
- **Fix deployed (Session 36)**: `enrich_article_with_ai` now only writes to `body` if body
  is currently empty (<200 chars). Raw scraped text is always preserved
- **Impact**: Economist avg body 2,132→5,898 chars; FA avg 2,500→11,469 chars after re-enrichment

### Re-enrichment completed
- Economist: 266 articles re-enriched — avg 2,132 → 5,898 chars ✅
- FA: 57 articles re-enriched — avg 2,500 → 11,469 chars ✅
- FT: 38 articles still need re-enrichment — blocked by ft_profile lock (launchd conflict)
  → These will self-correct on the next scheduled FT sync (05:40 or 11:40)
  → FT session was confirmed authenticated; selector was also updated (see FT section below)

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
  - Old template: `section.rich-text p` (added Session 36 — was causing "paywalled" false positives)
- Session: Drupal cookie `SSESS8d72...` valid until 2026-05-23
- 56/57 articles full text, avg 11,469 chars

### Bloomberg
- NO automated scraper — Bloomberg bot detection kills headless Playwright on homepage
- Bloomberg was previously attempted but removed due to bot detection
- All 38 Bloomberg articles added via Chrome Extension v1.3 clip button
- Workflow: open Bloomberg article in Chrome → click Meridian extension → "Clip Article"
- Extension detects bloomberg.com, extracts full text from DOM in real logged-in session
- No Bloomberg saved-articles sync — extension only clips individual open articles

### Bloomberg Chrome Extension (extension/ folder)
- Clip Article: scrapes current page DOM, sends to /api/articles (works for any source)
- Sync Bookmarks: bulk import from FT/Economist saved pages (NOT Bloomberg)
- Bloomberg is NOT in BOOKMARKS_PAGES — no bulk sync available
- Recommended: continue individual article clipping as needed

---

## Feed Source Restriction (Session 36)

Only FT/Economist/FA/Bloomberg articles are auto-saved to the main Feed (auto_saved=1).
All other sources (CNN, CFR, Foreign Policy, Atlantic Council, etc.) remain in Suggested only
regardless of relevance score. This keeps the Feed clean while preserving full analysis depth
(Suggested articles are still used by briefs and AI Analysis).

Implemented in server.py:
- `FEED_CORE_SOURCES = {'Financial Times', 'The Economist', 'Foreign Affairs', 'Bloomberg'}`
- `run_agent()` skips non-core sources — they stay in Suggested with status='new'
- Current Feed: 64 auto-saved articles (FT:30, Economist:21, FA:13) — all core sources ✅

---

## Key Themes (KT) System

### Current state (3 April 2026)
- 8 themes on VPS, sorted by article count descending
- key_facts: ⚠️ STILL BLANK — fix deployed (max_tokens 1500→2500) but all seeds ran before it
  → **Priority 1 next session: trigger Reset Themes on live site**
- getThemeArticles() now accepts both theme object OR numeric index (signature fix Session 36)

### kt_themes dedup bug — FIXED
- `/api/kt/themes` now filters by MAX(last_updated) — only latest seed returned
- If 16-theme accumulation happens again: delete stale rows on VPS by comparing last_updated

### Theme grid (Session 36)
- 8 AI themes sorted by matched article count (most articles top-left)
- ☆/★ star = permanent (gold border + badge), stored in localStorage `meridian_permanent_themes`
- 2 silver dashed manual slots with name/keywords/emoji modal, localStorage `meridian_manual_themes`
- Reset Themes confirm dialog lists permanent themes by name

### kt/seed pipeline
- Call 1: Sonnet, 165 sample titles → 8 themes. max_tokens=3000, timeout=60s
- Call 2: Haiku, batches of 50 → article→theme assignments
- Call 3: Haiku per theme → key_facts + subtopic_details. max_tokens=2500, timeout=45s

---

## Briefing Generator Tab (Session 36)

New third tab alongside News Feed and Key Themes. Flow:
1. Topic: All themes / Select a theme / Focused topic (+ Guidance textarea)
2. Time period: All coverage / Last month / Last week / Last 24h
3. Brief type: Short Brief / Full Intelligence Brief
4. Live article count preview updates as selections change
5. Generate button → existing kt-brief-modal with progress spinner

JS SyntaxError bug: literal newlines in template strings in bgGenerate() — fixed.
All three modes work: All themes uses AI Analysis pipeline; Select a theme uses
downloadBriefPDF; Focused topic uses custom Sonnet call with filtered article context.

---

## Chart/Image System

- 162 images (156 charts + 6 maps) across 88 Economist articles — all have AI insights
- Charts only appear in downloaded PDF briefs (Full Intelligence Brief), not modal text
- Capture guard: articles already in article_images are never re-captured
- **173 Economist articles have no images yet** — pending chart backfill
- **Priority: trigger POST /api/images/backfill on localhost** next session
  (runs Playwright against economist_profile, ~30 min, costs ~$0.03-0.05 in Haiku vision calls)
- After backfill completes: push images to VPS via wake_and_sync.sh

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

1. **Trigger Reset Themes** on live site — key_facts still blank, max_tokens fix deployed
   but no seed has run since. Go to meridianreader.com → Key Themes → Reset Themes.

2. **Chart backfill** — trigger POST /api/images/backfill on localhost (not VPS — scrapers
   run Mac-side). 173 Economist articles have no charts captured yet. ~30 min, ~$0.03.
   After completion: run wake_and_sync.sh to push images to VPS.

3. **FT 38 short articles** — will self-correct on next scheduled sync (05:40/11:40).
   New FT selector `div.n-content-body p` deployed. enrich fix deployed. No manual action needed.

4. **Clean up tmp_ files** — many accumulated this session. Run:
   git rm --ignore-unmatch tmp_*.py tmp_*.txt tmp_*.png && git commit -m "chore: remove tmp files"

5. **Trigger Reset Themes a second time if key_facts still blank** after #1 above.
   Inspect VPS log for "key_facts enrichment done" to confirm Call 3 ran.

6. **Sort theme articles by relevance** — detail panel shows most recent first; sort by
   keyword hit count + summary length.

7. **Sub-topics filtering** — chips do nothing; decide implement or remove.

8. **Focused Intelligence Briefing** — Briefing Generator tab now has this as "Focused topic"
   mode. Test and verify quality of output.

9. **FA session renewal** — Drupal cookie expires 2026-05-23. Before that date, open
   fa_profile Chromium and log in to foreignaffairs.com to refresh session.

10. **Checking server retry loop** — frontend shows Checking server during the ~8-10s
    Flask restart on every deploy. Add a JS retry loop (every 3s, up to 30s) so deploy
    restarts are invisible rather than showing an empty feed.

11. **ft_profile lock** — launchd sync owns ft_profile. Manual Playwright scripts run
    concurrently get a temp cookie-less copy, returning 0 chars. Safe window for manual
    FT Playwright work: outside 05:35-06:00 and 11:35-12:00. Or unload the sync plist:
    launchctl unload ~/Library/LaunchAgents/com.alexdakers.meridian.sync.plist
    (reload after with launchctl load)

---

## Build History

### 3 April 2026 (Session 36 — article health, body text fixes, feed cleanup)

**enrich_article_with_ai fullSummary overwrite bug — FIXED**
- Root cause: built before Playwright scrapers existed; always overwrote body with AI prose
- Fix: only writes to body if currently empty (<200 chars)
- Impact: Economist avg body 2,132→5,898; FA avg 2,500→11,469 after re-enrichment

**Economist re-enrichment** — 266 articles re-fetched via Playwright, real text stored

**FA re-enrichment** — all 57 articles now full text
- FA has two page templates: `div.article__body-content p` AND `section.rich-text p`
- `section.rich-text` selector added — was causing false "paywalled" detection for 9 articles
- Those 9 articles had 22,000-32,000 chars of available text; now correctly stored

**FT selector updated** — `div.n-content-body p` (FT changed CSS class names)
- Old selectors returned 0 paragraphs; new selector confirmed returning 14+ per article
- 38 FT articles still have AI summaries — will self-correct on next sync

**Feed source restriction**
- Only FT/Economist/FA/Bloomberg auto-saved to Feed (FEED_CORE_SOURCES)
- All other sources (CNN, CFR, FP, etc.) remain in Suggested only
- Current: 64 auto-saved articles, all core sources

**Briefing Generator tab** (from Session 35, completed)
- JS SyntaxError fixed (literal newlines in template strings)
- All three brief modes working

**getThemeArticles() signature fix**
- Function now accepts both theme object OR numeric index
- Was crashing with `Cannot read properties of undefined (reading 'keywords')`

**"Checking server" on deploy explained**
- Flask restarts for ~8-10s on every deploy.sh — not a real outage
- A retry loop in the frontend would hide this; to be built if annoying

**Bloomberg clarified**
- No automated scraper (bot detection too strong, previously attempted and removed)
- All 38 Bloomberg articles added via Chrome Extension clip button
- Correct workflow: open article → click extension → Clip Article

**534 articles pushed to VPS**

### 2 April 2026 (Session 35)
- FA selector fix (article__body-content), section.rich-text added
- Economist VPS backfill (push window removed)
- Key Themes crash fix (kt/themes MAX last_updated, null guard)
- Permanent/manual theme grid
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
