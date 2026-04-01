# Meridian — Technical Notes
Last updated: 1 April 2026 (Session 29 — complete)

## Overview
Personal news aggregator. Flask API + SQLite backend now running on Hetzner VPS (always-on).
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
  - meridian.html served with Cache-Control: no-cache (added Session 29)
  - sw.js served with Cache-Control: no-cache (added Session 29)
- GitHub: https://github.com/dakersalex/meridian-server (public)

## File Locations (VPS)
- /opt/meridian-server/server.py       — Flask API (port 4242)
- /opt/meridian-server/meridian.html   — Main frontend
- /opt/meridian-server/meridian.db     — SQLite database
- /opt/meridian-server/credentials.json — Anthropic API key + FA login
- /opt/meridian-server/venv/           — Python virtualenv (not in git)

## File Locations (Mac — local dev only)
- ~/meridian-server/server.py          — Flask API
- ~/meridian-server/meridian.html      — Main frontend
- ~/meridian-server/meridian.db        — Local database (not synced to VPS)
- ~/meridian-server/credentials.json   — Anthropic API key
- ~/meridian-server/cookies.json       — Publication session cookies
- ~/meridian-server/newsletter_sync.py — iCloud IMAP newsletter poller
- ~/meridian-server/extension/         — Chrome extension v1.3
- ~/meridian-server/brief_pdf.py       — Intelligence brief PDF generation module
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
View logs: journalctl -u meridian -f
Dump recent VPS logs to file: ssh root@204.168.179.158 "journalctl -u meridian --since '10 minutes ago'" > ~/meridian-server/vps_last_log.txt

## Deploying Code Updates
One command from Mac Terminal:
  cd ~/meridian-server && ./deploy.sh "description"

(deploy.sh: git add -A, commit, push, SSH pull on VPS, systemctl restart meridian)

## GitHub
Repo: https://github.com/dakersalex/meridian-server (public)
Token stored in Mac keychain (credential.helper osxkeychain)
Sensitive files excluded: credentials.json, cookies.json, meridian.db, newsletter_sync.py, venv/, *.wav, *.mp4, vps_last_log.txt

## Database (1 April 2026)
Total: ~508 articles (Mac), ~508 articles (VPS)
- Financial Times: 153
- The Economist: 257
- Foreign Affairs: 46
- Bloomberg: 38
- Other (CNN, Atlantic Council, Foreign Policy, CFR, Al Jazeera etc.): ~14

## Syncing
Note: Playwright scrapers still run on Mac via launchd (browser profiles not yet on VPS)
FT: Auto-syncs every 6h via launchd using Playwright + persistent profile (ft_profile/)
Economist: Auto-syncs every 6h via launchd using Playwright + persistent profile
Foreign Affairs: Auto-syncs every 6h via launchd using Playwright + fa_profile/
All quiet hours 1-6am.
Sync All button fires all 3 scrapers in parallel, then runs enrich_title_only_articles().
sync_now.py and meridian_sync.py both call enrich_title_only_articles() after sync — picks up agent-saved title_only articles.
wake_and_sync.sh now also pushes article_images to VPS after each sync (image push block added Session 28).

## Newsletter Pipeline
- iCloud alias: meridian.newsletters@icloud.com
- newsletter_sync.py polls iCloud IMAP (alex.dakers@icloud.com, app-specific password)
- iCloud IMAP: host=imap.mail.me.com, port=993, auth with primary address not alias
- iCloud requires BODY[] not RFC822 for fetch
- Stores in newsletters DB table: source, subject, body_html, body_text, received_at
- Flask route: /api/newsletters/sync (POST)
- Manual sync: curl -s https://meridianreader.com/api/newsletters/sync -X POST

## Title-only Enrichment
- enrich_title_only_articles() runs after every Sync All and every scheduled sync
- FT/Economist: uses logged-in Playwright profiles (ft_profile, economist_profile)
- Foreign Affairs: uses fa_profile
- Other sources: generic BeautifulSoup scrape, no login
- Routes: POST /api/enrich-title-only, GET /api/enrich-title-only/status

## Interviews & Briefings Tab
- DB table: interviews (id, title, url, source, published_date, added_date, duration_seconds, transcript, summary, speaker_bio, status, thumbnail_url)
- Status states: pending / needs_recording / transcribed / summarised
- Flask routes: GET /api/interviews, POST /api/interviews, PATCH /api/interviews/<id>, DELETE /api/interviews/<id>, POST /api/interviews/fetch-meta
- Speaker bio auto-generated by Claude on save
- Summary generated on demand via ✦ Generate summary button
- First entry: Sir Alex Younger, Inside Defence, Economist, 44m 57s, 7,740 words, summarised

## Video Transcript Pipeline
### yt-dlp approach (preferred):
~/Library/Python/3.9/bin/yt-dlp -f 140 --cookies-from-browser chrome -o "~/meridian-server/output.m4a" "YOUTUBE_URL"

### Economist DRM workaround (confirmed working):
1. Open article in Chrome, start playing video
2. DevTools → Network tab → filter "mp4"
3. Find rendition.m3u8?fastly_token=... → Right-click → Copy URL (token expires fast)
4. Download: ~/Library/Python/3.9/bin/yt-dlp "M3U8_URL" -o ~/meridian-server/interview.mp4
5. Convert: ffmpeg -i interview.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 interview.wav
6. Transcribe: ~/Library/Python/3.9/bin/whisper interview.wav --model small --language en --output_dir ~/meridian-server/ --output_format txt --verbose True
7. Auto-cleanup: audio files deleted automatically after transcript saved to DB

### Whisper notes:
- Use --model small (medium stalled on Python 3.9)
- FP16 warning on CPU is harmless
- Whisper hallucinating "U.S. Army" = silent/bad recording

## Suggested Articles Tab
### How it works
- DB table: suggested_articles (id, title, url, source, snapshot_date, score, reason, added_at, status, reviewed_at, pub_date)
- Status states: new / reviewed / saved / dismissed
- Inbox model — articles accumulate, no duplicates (URL dedup, normalised to strip query params)
- Saved articles (already in Feed) auto-excluded from view
- Nav badge shows new-count only
- Missing pub_date shows today's date as fallback

### Sources
- FT: Playwright scrapes ft.com homepage (logged in, 8 articles)
- Economist: Playwright scrapes most-read → /latest → homepage fallback (0-4 articles, intermittent)
- Web search: Claude (claude-sonnet-4-20250514 + web_search tool) searches FA, Foreign Policy, CFR, Atlantic Council etc.

### Scoring
- All sources scored by Claude 0-10 against interest profile (topics/tags from saved articles)
- Negative signal: dismissed article topics fed into scoring prompt as avoid_str
- Only articles scoring 6+ shown

### Refresh flow
1. Playwright scrapes FT + Economist in parallel threads (~10s)
2. Claude web search agentic loop (~40s, up to 6 roundtrips)
3. 30s delay (rate limit)
4. Pub_date lookup for Playwright articles without dates
5. 30s delay (rate limit)
6. Claude scores FT/Economist articles
7. Save new articles (URL dedup)
Total: ~2 minutes

### Scheduler (VPS — runs every 6h automatically, Mac not required)
- scrape_suggested_articles() runs on VPS scheduler
- Playwright part gets FT/Economist (works because Mac scrapers push profiles to VPS — actually VPS IP blocked, so Playwright gets 0 from FT/Economist on VPS)
- Claude web search finds FA, Foreign Policy, CFR, Atlantic Council etc. — works on VPS
- run_agent() runs after refresh, auto-saves articles scoring 8+ to Feed as title_only
- Next Mac sync picks up title_only articles and enriches to full_text

### Flask routes
- GET /api/suggested — accepts since=, status=, source= params
- POST /api/suggested/refresh
- GET /api/suggested/status
- PATCH /api/suggested/<id>
- POST /api/suggested/bulk-delete

### UI buttons
- 🔍 Find Articles — triggers suggested refresh (Suggested tab)
- 🔄 Sync all — triggers Mac Playwright scrapers + enrichment (activity bar)
- 📎 Clip Bloomberg — opens Bloomberg title-only articles for extension clipping (conditional)

## Autonomous Reading Agent
- run_agent() function, agent_log table, agent_feedback table
- POST /api/agent/run, GET /api/agent/log, POST /api/agent/feedback
- Runs automatically after every suggested refresh (VPS scheduler, every 6h)
- Auto-saved articles: status='agent', auto_saved=1 in DB
- ✦ Auto orange pill badge shown on Feed cards for agent-saved articles
- Curation filter in Feed: All / My saves / AI suggested
- Deleting agent-saved article shows feedback toast + writes to agent_feedback table
- agent_feedback feeds into scrape_suggested_articles() via avoid_str in scoring prompt

## AI Analysis
- Includes interviews in context (summary + transcript excerpt)
- Interest profile built from saved article topics/tags

## Bloomberg
- Scraping not viable (Cloudflare bot detection, no saved articles URL)
- Existing articles retained
- New articles via Chrome extension manual clip only
- 📎 Clip Bloomberg (N) button in activity bar: opens each title-only Bloomberg article with ?meridian_autoclip=1; extension auto-clips; button hidden when no BBG title-only articles

## Schedule (Geneva/CEST time)
- 05:40 — Mac wakes (pmset), Playwright scrapes FT + Economist + FA
- 05:50 — VPS scores articles, agent auto-saves 8+ to Feed
- 06:00 — Fresh articles ready to read ✅
- 11:40 — launchd fires wake_and_sync.sh, Playwright scrapes again
- 11:50 — VPS scores again
- 12:00 — Fresh articles ready for lunchtime ✅

VPS scheduler: fixed UTC times 03:50 and 09:50 (= 05:50 and 11:50 CEST)
Mac pmset: wakepoweron at 05:40 daily
Mac launchd: com.alexdakers.meridian.wakesync runs at 05:40 and 11:40

## Economist Scraper (Session 13 overhaul)
- Source: economist.com homepage (not bookmarks — Cloudflare blocks that)
- headless=False to bypass Cloudflare challenge page
- Persistent profile: economist_profile/ (login session saved, no daily login needed)
- Flow: open homepage → collect all article titles+URLs → filter section labels → Claude scores titles → save passing articles as title_only → enrich_title_only_articles() fetches full text on next Mac sync
- Title filters: length ≥ 20 chars, word count > 4, no & with ≤ 5 words (removes section labels)
- Scoring: claude-haiku-4-5-20251001, explicit score bands:
  - 8-10: geopolitics, war, sanctions, central banking, financial markets, trade policy, macro economics, energy markets, international relations, diplomacy
  - 5-7: business strategy, corporate finance, technology policy, regulatory affairs, emerging markets
  - 0-4: lifestyle, health, science, culture, arts, sport, food, travel, personal finance, music, brain science, fitness
- Checks ALL homepage articles (no early-exit on first existing article)
- Cap: 8 articles max after scoring
- Articles saved as title_only, full text fetched by enrich_title_only_articles() on next Mac sync
- call_anthropic() fix: json.dumps(payload, ensure_ascii=False).encode('utf-8') — fixes 400 errors from curly apostrophes in titles
- Confirmed working: 15/21 articles scored 6+, 6 filtered (music, church, moon etc.), 8 saved as title_only

## Economist Chart & Map Capture (Session 26 — BUILT ✅)

### What was built
- `article_images` DB table added to init_db()
- `capture_economist_charts(page, article_id)` helper function in server.py
- Hooked into `enrich_title_only_articles()` Economist block — runs after each article is fetched while page is still open
- Three new Flask routes:
  - GET /api/articles/<aid>/images — returns images as base64 JSON (includes insight field)
  - POST /api/images/backfill — async job, captures charts from all existing Economist articles
  - GET /api/images/backfill/status — poll progress
- All deployed to VPS and Mac (commit c5603391)

### How capture_economist_charts() works
1. Scrolls page fully to trigger lazy-loading
2. Finds all `<figure>` elements whose `<figcaption>` contains "chart:" or "map:" (lowercase — actual Economist format: "chart: the economist" / "map: the economist")
3. Scrolls each figure into view, screenshots as PNG via element.screenshot()
4. Calls Claude Haiku vision API for one-line description (max 25 words)
5. Saves to article_images (idempotent — skips if article already has images)

### article_images DB schema
```sql
CREATE TABLE IF NOT EXISTS article_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id TEXT NOT NULL,
    caption TEXT NOT NULL,
    description TEXT DEFAULT '',
    insight TEXT DEFAULT '',
    image_data BLOB NOT NULL,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    captured_at INTEGER NOT NULL,
    mac_id INTEGER DEFAULT NULL,
    FOREIGN KEY (article_id) REFERENCES articles(id)
)
```
Note: `mac_id` column added in Session 28 via ALTER TABLE migration in push-images route.
It stores the Mac autoincrement PK to enable correct dedup of multi-chart articles
(all Economist charts share the same caption "chart: the economist", so (article_id, caption)
is not unique — mac_id is the correct dedup key).

### Image insight enrichment (Session 27)
- `article_images` table: `insight` column added (ALTER TABLE migration in init_db)
- `enrich_image_insights()` function: Haiku vision call per image, passes article title + summary + description as context, generates 30-word analytical insight string
- `POST /api/images/enrich-insights` — async job, processes all images with empty insight
- `GET /api/images/enrich-insights/status` — poll progress
- VPS scheduler: after each run, auto-triggers kt/tag-new and enrich_image_insights
- Insight format: "what analytical point this chart supports in the context of its source article"
- Brief pipeline uses both `description` (visual) and `insight` (contextual) for relevance scoring

### Image sync to VPS (Session 28)
- POST /api/push-images route added to server.py — receives image rows from Mac, upserts into VPS DB
- Deduplicates on mac_id (not article_id+caption — see schema note above)
- wake_and_sync.sh updated to push images after every article push
- All 153 Mac images manually pushed to VPS (Session 28) — VPS now has 153 rows (87 legacy rows deleted Session 29)
- reportlab installed in VPS venv (required for PDF generation)

### Brief image selection logic (CURRENT — Session 29)

#### Chart display in briefs
- Charts appear with NO caption — the image already contains its own title, axis labels and source
- description and insight are INTERNAL ONLY — used by the pipeline for relevance scoring, never shown to reader
- Charts only appear in the FULL brief, not the short brief
- Layout: inline within sections, ALWAYS 2 per row (never a solo chart)
- Both images in a pair are normalised to the same height to prevent cropping/misalignment

#### Chart selection rules (Session 29 overhaul)
- No charts in: Executive Summary, Overview, Cross-cutting Themes, Strategic Implications, Watch List, Key Developments, Source Notes
- Charts only placed in named subtopic sections
- Never a solo chart — if only 1 qualifies for a section, that section gets 0
- Cross-brief similarity dedup: if a chart's description is >50% similar to one already placed anywhere in the brief, it is rejected — prevents similar maps/charts appearing in different sections
- Budget: up to 2 per section, global cap 14, minimum budget of 2 required before attempting a section
- Minimum score threshold: 2 (prevents loose single-word matches)
- Prompt instructs Sonnet: "Do NOT include a title heading or overview section" — kills the spurious `# Theme — Intelligence Brief` line

#### DB fields used
- article_images.description — what the chart shows visually (25 words, generated at capture time)
- article_images.insight — what analytical point it supports in context of source article (30 words)
- Both confirmed fully populated: 153/153 images on Mac as of 31 March 2026

## Intelligence Brief Pipeline (Sessions 28-29 — FULLY WORKING ✅)

### Overview
- brief_pdf.py — standalone module, ReportLab Platypus, generates A4 PDF
- Clicking "Short Brief" or "Full Intelligence Brief" opens a modal with the text brief + "Open as PDF ↗" button
- The PDF job runs in parallel in the background while you read the text brief
- Full brief includes Economist charts inline (subtopic sections only); short brief is text only
- reportlab installed: Mac (pip3) and VPS venv

### User flow (current design)
1. Click "Short Brief" or "Full Intelligence Brief" on any theme
2. Modal opens immediately showing a loading spinner with rotating progress messages and elapsed time
3. ~60-90s later the text brief renders in the modal (readable immediately)
4. "Open as PDF ↗" button top-right of modal — click to open the fully-formatted PDF with charts in a new tab
5. The PDF was generating in parallel so it's usually ready by the time you've read the first section

### Progress messages during generation (Session 29)
- Modal shows rotating step labels (e.g. "Reading 200+ articles…", "Assessing energy threats…") + elapsed seconds
- Button shows elapsed seconds ticking up (e.g. "42s…")
- Both reset cleanly when the brief arrives or errors

### Flask routes
- POST /api/kt/brief — text brief (async job), returns {ok, job_id}
- GET /api/kt/brief/status/<job_id> — poll {status, brief, error}
- POST /api/kt/brief/pdf — PDF job (async), returns {ok, job_id}
- GET /api/kt/brief/pdf/status/<job_id> — poll {status, ready, size, error}
- GET /api/kt/brief/pdf/download/<job_id> — download/open completed PDF

### brief_pdf.py key learnings
- Original file had pervasive heredoc corruption (literal newlines inside Python string literals)
- Rewritten from scratch via Filesystem MCP in Session 28
- NEVER write brief_pdf.py via heredoc or shell — always use filesystem:write_file
- Same applies to any JS file with regex literals — patch scripts must use filesystem:write_file
  and binary-safe replacements to avoid corrupting `/` in regex patterns

### Service worker & caching (Session 29)
- sw.js cache version: meridian-v5 (bumped Session 29 to force cache invalidation)
- sw.js is now properly committed and deployed (was empty on VPS in Session 28)
- nginx serves meridian.html and sw.js with Cache-Control: no-cache so clients always get latest
- If clients are stuck on old code: DevTools → Application → Service Workers → Unregister, then hard refresh

## Autonomous Mode (Claude in Chrome + shell endpoint)

### How it works
Claude can deploy code, run shell commands, and check logs entirely without you doing anything.
This requires THREE things to be true at the same time:

1. **Claude in Chrome extension** is installed in Chrome and connected to the active Claude conversation
   - Extension connects to a specific conversation — a new chat window loses this connection
   - To reconnect in a new chat: open the extension popup and click "Connect" (or it reconnects automatically)
2. **Meridian tab** is open at http://localhost:8080/meridian.html in Chrome
   - Claude runs JS in this tab to reach localhost:4242
3. **Mac Flask server** is running at localhost:4242 (auto-starts on login via launchd)

### Shell endpoint
- Flask route: POST /api/dev/shell (localhost only — 127.0.0.1 and ::1 only)
- Claude calls it via JS in the Meridian browser tab:
  ```js
  window.shell = (cmd) => fetch('http://localhost:4242/api/dev/shell', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({cmd})
  }).then(r=>r.json());
  window.shell('cd ~/meridian-server && ./deploy.sh "message"').then(d=>console.log(d.stdout));
  ```
- Claude reads results via read_console_messages tool (Claude in Chrome)

### What MCP provides
Two MCP servers run automatically in the background — you never start them manually:
1. **Filesystem MCP** — configured in Claude Desktop, gives Claude read/write access to ~/meridian-server/
   Configured at: /opt/homebrew/bin/npx @modelcontextprotocol/server-filesystem /Users/alexdakers/meridian-server
2. **Claude in Chrome MCP** — the Chrome extension itself is an MCP server, gives Claude access to browser tabs
   Visible as the orange-outlined tab group labelled "✅ Claude (MCP)" in your Chrome tab strip

### Pre-flight checklist before starting a new session (DO THIS FIRST)
These three steps prevent the stale-MCP and Flask-down issues seen in Session 26/27:

1. **Close all old Claude MCP tab groups in Chrome**
   - Look for tabs labelled `Claude (MCP)` or `✅ Claude (MCP)` from previous sessions
   - Close them all — only one MCP tab group should exist at a time
   - The new chat will create a fresh one automatically

2. **Verify Flask is running**
   - Visit http://localhost:4242/api/health in a browser tab
   - Should return `{"ok":true,"version":"3.0.0"}`
   - If it doesn't respond, run this once in Terminal:
     `launchctl unload ~/Library/LaunchAgents/com.alexdakers.meridian.plist; sleep 2; launchctl load ~/Library/LaunchAgents/com.alexdakers.meridian.plist`

3. **Then open the new Claude chat and paste the opener prompt**
   - The extension connects automatically, Claude creates a fresh MCP tab group and runs the health check

### IMPORTANT: Never restart Flask through the shell endpoint
The shell endpoint is served by Flask itself. Sending a restart command through it kills Flask
mid-response, leaving launchd to restart it in an unknown state. Instead:
- For Mac Flask restarts: write a script via Filesystem MCP and trigger via osascript
- Claude should NEVER run `launchctl unload` via the shell endpoint

### Starting a new autonomous session
1. Complete pre-flight checklist above
2. Open claude.ai in Chrome and start a new chat
3. Paste the opener prompt (see Session Starter Prompt section below)
4. Claude reads NOTES.md, runs health check, reports state, proceeds autonomously

**No Terminal needed for anything except Flask restart if it's down.**
**Note:** raw.githubusercontent.com is blocked in Claude's network allow-list, so fetching from GitHub URL does not work.
**Important:** Keep only ONE Chrome window open per session. Two windows = two MCP tab groups = confusion about which tab Claude is controlling.

### If autonomous mode isn't working
- Check the ✅ Claude (MCP) tab exists in Chrome — if missing, tell Claude and it will recreate it
- Check extension is connected: click the asterisk icon in toolbar, should show green Connected dot
- Verify Mac server is running: http://localhost:4242/api/health in browser
- If Flask is down: Terminal → `launchctl unload ~/Library/LaunchAgents/com.alexdakers.meridian.plist; sleep 2; launchctl load ~/Library/LaunchAgents/com.alexdakers.meridian.plist`
- Do NOT close the ✅ Claude (MCP) tab — it's infrastructure, not a regular browser tab

### Autonomous working principles (important for new sessions)
Claude operates fully autonomously and never asks the user to check, refresh, or verify anything.

**Verification loop (used for all fixes):**
1. Query the API directly with `{cache: 'no-store'}` to check current state
2. Query the DOM on the meridianreader.com MCP tab via `javascript_tool`
3. Apply the fix (edit file via Filesystem MCP, deploy via shell endpoint)
4. Re-verify by querying API/DOM again
5. Report the confirmed result to the user — never say "please check" or "please refresh"

**Clearing stale UI cache (after deploys):**
```js
// Run on meridianreader.com MCP tab
navigator.serviceWorker.getRegistrations().then(regs => regs.forEach(r => r.unregister()));
caches.keys().then(keys => keys.forEach(k => caches.delete(k)));
```
Then navigate the tab to `https://meridianreader.com/meridian.html` and reload.
Note: nginx now serves meridian.html with no-cache headers so hard refresh always gets latest.

**When a user reports a JS syntax error / page not loading:**
- Check browser console for SyntaxError — often a literal newline inside a regex or string
- Root cause: patch scripts that use Python string literals can embed real \n inside JS regexes
- Fix: use filesystem:write_file for all file writes, and binary-safe replacements for regex patches

**When a user reports a visual bug:**
- Never ask them to refresh or check
- Verify it appears in the DOM on the MCP tab
- Check the API to confirm if it's a data issue vs cache issue
- Fix the root cause, clear cache if needed, screenshot to verify, report back

### Deploy pattern (Claude uses this)
```js
window.shell('cd ~/meridian-server && ./deploy.sh "description"')
  .then(d => window.shell('ssh root@204.168.179.158 "cd /opt/meridian-server && git fetch origin && git reset --hard origin/main && systemctl restart meridian && echo Done"'));
```

### VPS Python pattern (ALWAYS use this — never inline -c strings)
Never use `ssh root@... "python3 -c '...'"` for anything non-trivial — nested quote escaping always fails.
Instead: write script via Filesystem MCP, scp it, run it:
```js
// 1. Write script to Mac (use filesystem:write_file)
// 2. SCP and run
window.shell('scp ~/meridian-server/tmp_script.py root@204.168.179.158:/tmp/ && ssh root@204.168.179.158 "python3 /tmp/tmp_script.py"')
  .then(d => console.log('OUT:', d.stdout));
```
For simple one-liners, use sqlite3 CLI on Mac instead of SSH.

### Session start checklist (Claude runs this automatically)
At the start of every session, Claude should:
1. Call `tabs_context_mcp` to get current tab IDs
2. Navigate the secondary MCP tab to `https://meridianreader.com/meridian.html` (for DOM verification)
3. Run the health check via shell endpoint:
```js
window.shell(`
  echo '=== Flask ===' && curl -s http://localhost:4242/api/health &&
  echo '=== DB ===' && sqlite3 ~/meridian-server/meridian.db "SELECT source, COUNT(*), SUM(status='title_only') as pending FROM articles GROUP BY source" &&
  echo '=== Enrichment ===' && curl -s http://localhost:4242/api/enrich-title-only/status &&
  echo '=== KT ===' && curl -s http://localhost:4242/api/kt/status &&
  echo '=== Images ===' && curl -s http://localhost:4242/api/images/backfill/status &&
  echo '=== Last log ===' && tail -3 ~/meridian-server/logs/server.log
`).then(d => console.log('HEALTH:', d.stdout));
```
This gives immediate awareness of: Flask status, DB counts, pending enrichments, KT seed state, image backfill state, last sync.

### Dangerous operations checklist (ALWAYS follow before bulk deletes)
Before any DELETE, UPDATE affecting multiple rows, or destructive operation:
1. Run a SELECT first — preview exactly what will be affected with LIMIT 5
2. State explicitly in the response: what is being deleted, why, and what it will NOT delete
3. Only then execute the destructive operation
4. Verify row count after: `SELECT changes()` or re-query to confirm

Lesson from Session 19: deleted all auto_saved=0 Economist articles assuming they were junk —
they were actually all user bookmarks. A preview SELECT would have caught this immediately.

### Tab setup for autonomous sessions
Two MCP tabs are needed for full autonomy:
- **Tab A** (localhost:8080/meridian.html) — shell bridge for running commands
- **Tab B** (meridianreader.com/meridian.html) — live site for DOM inspection and visual verification

TabIds change every session. Always call `tabs_context_mcp` first to get current IDs,
then navigate Tab B to the live site if it isn't already there.

## Mobile PWA (Session 14-15)
- Media query: @media (max-width: 1400px) and (pointer: coarse)
- Fixed header stack: masthead (top:0), server-bar (top:55px), main-nav (top:93px)
- iPad measured heights: mH:55, sH:38, nH:37 → navTotal=130px
- Mobile filter bar (#mobile-filter-bar) fixed at top:130px, pushes main-layout to margin-top:160px
- Pull-to-refresh REMOVED (was causing layout gap issues)
- Filter bar hidden on desktop, shown on mobile — Source / Time / Curation dropdowns
- Masthead on mobile: tagline+date hidden, flex-wrap:nowrap, logo 20px
- feed-header-outer (desktop filters) hidden on mobile via display:none
- No JS for header positioning — pure CSS only

## Backup & Recovery

### What is backed up
- **GitHub** (`github.com/dakersalex/meridian-server`) — all code, NOTES.md, scripts. Every session is a git commit so any prior version is recoverable via `git checkout <hash>`
- **VPS DB** (`/opt/meridian-server/db_backups/`) — daily backup of Mac `meridian.db` at 23:00, 7 days retained
- **VPS DB itself** — has all articles ever pushed from Mac (~508 articles)

### What is NOT on GitHub (by design — sensitive)
- `meridian.db` — article database (backed up to VPS nightly)
- `credentials.json` — Anthropic API key + FA login
- `newsletter_sync.py` — has iCloud credentials
- Browser profiles (`ft_profile/`, `economist_profile/`, `fa_profile/`) — Playwright login sessions

### Recovery scenarios
**Lost Mac DB** → `scp root@204.168.179.158:/opt/meridian-server/db_backups/meridian_mac_YYYY-MM-DD.db ~/meridian-server/meridian.db`
**Lost all code** → `git clone https://github.com/dakersalex/meridian-server`
**Lost VPS** → Rebuild from GitHub + restore DB from local Mac backup
**Lost everything** → GitHub has all code; article DB is gone beyond last VPS push (worst case lose unsynced Mac-only articles)

### Daily backup
- Script: `~/meridian-server/backup_db.sh`
- Runs: daily at 23:00 via launchd (`com.alexdakers.meridian.dbbackup`)
- Destination: `root@204.168.179.158:/opt/meridian-server/db_backups/meridian_mac_YYYY-MM-DD.db`
- Retention: 7 days

## Next Steps (priority order)
1. **PWA icons** — proper 192x192 and 512x512
2. **Newsletter auto-sync** — newsletter_sync.py gitignored; VPS cannot auto-sync
3. **Clean up tmp_ files** — many tmp_*.py and tmp_*.sh files committed to repo during Sessions 28-29; worth a housekeeping commit to remove them
4. **Charts in modal preview** — currently modal shows text only; charts only in PDF. Could add inline chart images to modal by fetching /api/articles/<id>/images for each article and injecting as <img> tags. Deferred — not a blocker.

## Session 29 — Complete build log (1 April 2026)

### Context
Session 29 was primarily a brief pipeline polish session, triggered by Alex reviewing the Iran War full brief PDF and identifying several quality issues.

### Issues found and fixed

#### brief_pdf.py — chart selection overhaul (commit 24d4e6d6)
- No charts in Executive Summary, Overview, or prose-only sections — charts now subtopic-only
- Never a solo chart — score_charts_for_section returns [] if only 1 chart qualifies; budget loop requires ≥2 remaining
- Cross-brief similarity dedup: placed_descs list tracks all placed chart descriptions; new candidates rejected if >50% similar — kills duplicate maps/charts across sections
- Aligned image heights: both images in a pair normalised to same height (min of the two natural heights, capped at 7cm) — fixes the mismatched/cropped pair issue
- Prompt updated to instruct Sonnet not to generate title heading or overview section

#### Brief modal UX overhaul (commits 6eb96e61, b1f3bde5, fa0be720)
- Brief now renders as text in existing modal (not auto-download)
- "Open as PDF ↗" button in modal header — opens PDF in new tab via direct user click (no popup blocker)
- PDF job starts in parallel with text generation so it's usually ready when user clicks the button
- Progress ticker: modal shows rotating step labels + elapsed seconds during generation
- Button shows elapsed seconds ticking up
- `# Title` lines stripped from modal markdown renderer

#### Service worker / caching crisis (commits 39b35a50, b0caec46)
- Root cause: VPS had empty sw.js — some previous service worker (meridian-v4 or earlier) was installed in browsers and caching old meridian.html indefinitely
- Fix: bumped cache version to meridian-v5, deployed correct sw.js to VPS
- nginx updated to serve meridian.html and sw.js with Cache-Control: no-cache
- JS syntax error caused by patch script embedding literal newlines inside regex literals — fixed with binary-safe Python replacements

#### Regex corruption incident
- Patch script that wrote downloadBriefPDF embedded literal newlines inside two JS regexes:
  `(<li>.*<\/li>\n?)` → split across two lines; `/\n\n/g` → real newlines inside regex
- Result: SyntaxError on page load, SERVER undefined, entire app broken
- Fix: tmp_fix_regex.py used binary replacement to restore escaped sequences
- Lesson: ALWAYS use filesystem:write_file for JS files; NEVER construct JS with Python string interpolation that includes backslash sequences

### DB state end of Session 29
- Total articles: ~508 (Mac + VPS)
- article_images VPS: 153 (87 legacy rows deleted)
- Last commit: fa0be720

## Build History
### 1 April 2026 (Session 29)
- Brief modal: text preview + "Open as PDF ↗" button replacing auto-download
- Progress ticker during brief generation (rotating steps + elapsed time)
- brief_pdf.py: no solo charts, cross-brief dedup, aligned heights, no overview section
- sw.js fixed and deployed (was empty on VPS), cache bumped to v5
- nginx: no-cache headers for meridian.html and sw.js
- JS regex corruption fixed (literal newlines in patch scripts)
- 87 legacy article_images rows deleted from VPS

### 31 March 2026 (Session 28)
- brief_pdf.py rewritten and deployed — heredoc corruption fixed end-to-end
- PDF download buttons wired for both short and full briefs
- article_images sync Mac→VPS implemented (push-images route + wake_and_sync.sh)
- mac_id dedup fixed for multi-chart articles
- 153 images pushed to VPS; Iran full brief verified at 960KB with embedded charts

### 31 March 2026 (Session 27)
- Chart capture fix: figcaption case mismatch fixed (commit 44cd1852)
- Backfill: 153 images captured from 247 Economist articles
- insight column added to article_images
- enrich_image_insights(): 153/153 images enriched
- Chart display design finalised; brief pipeline design locked

### 31 March 2026 (Session 26)
- Built Economist chart capture end-to-end
- article_images table, capture_economist_charts(), backfill route
- Deployed to VPS and Mac (commit c5603391)

### 30 March 2026 (Sessions 23-25)
- Key Themes: KT incremental architecture, async generation, article grid, pub_date normalisation

### 29 March 2026 (Sessions 18-22)
- Key Themes feature built end-to-end; activity bar, autonomous verification, Economist junk filter

### 28 March 2026 (Sessions 13-17)
- Economist scraper overhaul, mobile PWA, shell endpoint, VPS sync, newsletters

### 28 March 2026 (Sessions 8-12)
- Auto badge, curation filter, agent feedback, VPS scheduler, Bloomberg clip, iPad PWA, reading agent

### 26-27 March 2026 (Sessions 1-7)
- meridianreader.com live, VPS, GitHub, all core features built

## GitHub Visibility
- Repo is currently PUBLIC: github.com/dakersalex/meridian-server
- No sensitive files in repo (credentials.json, cookies.json, meridian.db excluded)

## Session Starter Prompt
Copy and paste this at the start of each Claude session:

---
You are helping me build Meridian, my personal news aggregator. Please read my technical notes from the Filesystem MCP at /Users/alexdakers/meridian-server/NOTES.md and review them. Then run the session start health check.
---

**Note for Claude reading this:** At the start of every session you must:
1. Read NOTES.md via Filesystem MCP (path above) — do NOT try to fetch from GitHub URL (blocked)
2. Check Flask is up by testing the shell endpoint — if it doesn't respond, report clearly and stop; do NOT attempt to restart Flask via the shell endpoint (it kills itself)
3. Run the health check and report results before asking what to work on
