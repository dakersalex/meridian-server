# Meridian — Technical Notes
Last updated: 30 March 2026 (Session 25 — complete)

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
Restart nginx: systemctl restart nginx
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

## Database (30 March 2026)
Total: ~503 articles (Mac), ~493 articles (VPS)
- Financial Times: 150
- The Economist: 254
- Foreign Affairs: 44
- Bloomberg: 38
- Other (CNN, Atlantic Council, Foreign Policy, CFR, Al Jazeera etc.): ~17

## Syncing
Note: Playwright scrapers still run on Mac via launchd (browser profiles not yet on VPS)
FT: Auto-syncs every 6h via launchd using Playwright + persistent profile (ft_profile/)
Economist: Auto-syncs every 6h via launchd using Playwright + persistent profile
Foreign Affairs: Auto-syncs every 6h via launchd using Playwright + fa_profile/
All quiet hours 1-6am.
Sync All button fires all 3 scrapers in parallel, then runs enrich_title_only_articles().
sync_now.py and meridian_sync.py both call enrich_title_only_articles() after sync — picks up agent-saved title_only articles.

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
- Anthropic API credits exhausted mid-session — topped up at console.anthropic.com/settings/billing
- Confirmed working: 15/21 articles scored 6+, 6 filtered (music, church, moon etc.), 8 saved as title_only

## Economist Chart & Map Capture — Design Spec (Session 25)

### Discovery
- Economist charts and maps are static PNG images served from their CDN (content-assets/images/*.png)
- NOT D3/JS components — they render reliably and are screenshottable via Playwright element.screenshot()
- Each chart/map is wrapped in a <figure class="css-3mn275 e1197rjj0"> element
- Caption is in <figcaption class="css-1dkrsla e15o9k8g2"> containing exactly "Chart: The Economist" or "Map: The Economist"
- Confirmed working: Playwright element screenshot of figure captures chart + caption cleanly
- Test article: "How Iran is making a mint from Donald Trump's war" — 4 figures captured successfully
  - Figure 1: Iran contraband bar chart (oil tankers, Strait of Hormuz) — 60,468 bytes
  - Figure 2: Kharg Island map + satellite imagery — 241,508 bytes
  - Figure 3: Chart (oil exports) — 60,468 bytes
  - Figure 4: Chart — 60,468 bytes

### Capture approach
During enrich_title_only_articles(), after fetching full text for Economist articles:
1. Find all <figure> elements whose <figcaption> contains "Chart:" or "Map:"
2. Scroll each into view (lazy-load trigger — page must be scrolled fully first)
3. Use Playwright element.screenshot() to capture figure + caption as PNG
4. Generate a one-line AI description of what the chart shows (Claude Haiku, cheap)
5. Store in article_images table

### DB schema (to be added to init_db)
```sql
CREATE TABLE IF NOT EXISTS article_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id TEXT NOT NULL,
    caption TEXT NOT NULL,          -- "Chart: The Economist" or "Map: The Economist"
    description TEXT DEFAULT '',    -- AI one-liner: "Bar chart showing Iran-linked oil tankers..."
    image_data BLOB NOT NULL,       -- PNG bytes
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    captured_at INTEGER NOT NULL,
    FOREIGN KEY (article_id) REFERENCES articles(id)
)
```

### Brief image selection logic (IMPORTANT — agreed design)
- Charts are only included in a brief if their description has meaningful term overlap with the brief text
- This is a two-pass process:
  1. First pass: generate the brief text as normal
  2. Second pass: score each candidate chart description against the brief text
     - Include chart if key terms in description appear in brief (e.g. "Hormuz", "tankers", "Iranian oil")
     - Exclude chart if no overlap with brief content, regardless of theme
- Cap at 3-4 images per brief section, 6-8 per full brief
- Prioritise most recently published and highest relevance score
- A chart from one article CAN appear in a brief driven by a different article if subject matter overlaps
- Charts that are not mentioned/relevant to the brief's key points are EXCLUDED entirely

### Backfill plan
After chart capture is built, run a one-time backfill across all 254 Economist articles via Playwright:
- Use economist_profile/ persistent session (already logged in)
- Process articles in batches to avoid Cloudflare rate limits
- Expected: ~30-60 minute job, ~500-1000 chart/map images captured
- Route: POST /api/images/backfill (async job, poll for status)

### Build order
1. Fix KT JS syntax error (current blocker) ← NEXT
2. Run KT seed (90 seconds, $0.07)
3. Build chart capture (new article_images table, Playwright capture in enrich_title_only_articles, AI description, backfill route)
4. Wire charts into briefs (two-pass relevance scoring, embed in PDF)

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

### Starting a new autonomous session
1. Open claude.ai in Chrome and start a new chat
2. Paste this as your opening message:
   > You are helping me build Meridian, my personal news aggregator. Please read my technical notes from the Filesystem MCP at /Users/alexdakers/meridian-server/NOTES.md and review them. Then run the session start health check.
3. The Claude in Chrome extension (v1.0.64+) connects automatically — no manual Connect click needed
4. The extension opens an MCP tab group (orange-outlined tabs labelled ✅ Claude (MCP))
5. Claude reads NOTES.md via Filesystem MCP, runs health check, and confirms ready

**No Terminal needed** — Claude reads NOTES.md directly via Filesystem MCP.
**Note:** raw.githubusercontent.com is blocked in Claude's network allow-list, so fetching from GitHub URL does not work.
**Important:** Keep only ONE Chrome window open per session. Two windows = two MCP tab groups = confusion about which tab Claude is controlling.

### If autonomous mode isn't working
- Check the ✅ Claude (MCP) tab exists in Chrome — if missing, tell Claude and it will recreate it
- Check extension is connected: click the asterisk icon in toolbar, should show green Connected dot
- Verify Mac server is running: curl http://localhost:4242/api/health
- Server restart: launchctl unload ~/Library/LaunchAgents/com.alexdakers.meridian.plist && launchctl load ~/Library/LaunchAgents/com.alexdakers.meridian.plist
- Do NOT close the ✅ Claude (MCP) tab — it's infrastructure, not a regular browser tab

### Autonomous working principles (important for new sessions)
Claude operates fully autonomously and never asks the user to check, refresh, or verify anything.

**Verification loop (used for all fixes):**
1. Query the API directly with `{cache: 'no-store'}` to check current state
2. Query the DOM on the meridianreader.com MCP tab via `javascript_tool`
3. Apply the fix (edit file via Filesystem MCP, deploy via shell endpoint)
4. Re-verify by querying API/DOM again
5. Take a screenshot of the meridianreader.com MCP tab to visually confirm
6. Report the confirmed result to the user — never say "please check" or "please refresh"

**Clearing stale UI cache (after deploys):**
```js
// Run on meridianreader.com MCP tab
navigator.serviceWorker.getRegistrations().then(regs => regs.forEach(r => r.unregister()));
localStorage.clear(); sessionStorage.clear();
```
Then navigate the tab to `https://meridianreader.com/meridian.html` and screenshot to confirm.

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
// 1. Write script to Mac
// (use filesystem:write_file)
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
  echo '=== Last log ===' && tail -3 ~/meridian-server/logs/server.log
`).then(d => console.log('HEALTH:', d.stdout));
```
This gives immediate awareness of: Flask status, DB counts, pending enrichments, KT seed state, last sync.

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
- **VPS DB itself** — has all articles ever pushed from Mac (~493 articles)

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
1. **Economist chart capture** — build article_images table + Playwright capture in enrich_title_only_articles + AI description + backfill route. See design spec above.
2. **Wire charts into briefs** — two-pass relevance scoring, embed in PDF
3. **Wire /api/kt/tag-new into VPS scheduler** — runs after each sync to tag new articles
4. **PWA icons** — proper 192×192 and 512×512 instead of placeholders
5. **Newsletter auto-sync** — newsletter_sync.py is gitignored (has credentials), so VPS can't auto-sync

## KT Incremental Architecture — Current Build State

### What is complete ✅
- server.py: 3 new DB tables in init_db(): article_theme_tags, kt_themes, kt_meta
- server.py routes all deployed to VPS and working:
  - POST /api/kt/seed + GET /api/kt/seed/status/<job_id> — async full seed with polling
  - GET /api/kt/themes — returns themes from DB (returns {seeded:false} if not yet seeded)
  - GET /api/kt/status — seeded state, counts, pending evolution
  - POST /api/kt/tag-new — tags untagged articles with Haiku in batches of 50
  - POST /api/kt/evolve — detects theme replacement candidates, writes to kt_meta as pending_evolution
- meridian.html fully patched and working:
  - renderKeyThemes() calls loadThemes() (DB-backed, instant)
  - loadThemes() → shows seed prompt if not seeded, renders grid if seeded
  - seedThemes() → fires /api/kt/seed, polls for progress, renders grid on completion
  - generateThemes() → thin wrapper calling loadThemes()
  - Reset Themes button wipes all tables and re-seeds
  - Evolution banner shown when pending_evolution detected
  - localStorage caching removed entirely
- Seed successfully run on VPS: 10 themes, 488/493 articles tagged ✅
- 5 untagged articles are title_only stubs — will be tagged on next sync via /api/kt/tag-new

### Seed architecture (final working design)
Two-call approach:
1. Call 1 (Sonnet, 3000 tokens, 60s timeout): send every 3rd article as representative sample (~165 titles) → generate 10 lean themes (name, emoji, keywords, overview, subtopics only — NO key_facts/subtopic_details)
2. Call 2 (Haiku, 2000 tokens, 30s timeout): assign all 494 articles to themes in batches of 50 (~10 batches × ~10s each)
key_facts and subtopic_details are generated on-demand when user clicks a theme (existing /api/kt/generate route)

### 10 themes seeded (30 March 2026)
- ⚔️ Iran War and Geopolitical Crisis — 108 articles
- 🇪🇺 European Economic and Political Challenges — 117 articles
- 📈 Global Financial Markets Volatility — 91 articles
- 🐉 China-US Strategic Competition — 92 articles
- 🏛️ Trump Administration Foreign Policy — 84 articles
- 🤖 Artificial Intelligence Revolution — 78 articles
- 🛢️ Energy Markets and Security — 78 articles
- 🏢 Corporate Strategy and Innovation — 79 articles
- 🌍 Trade Wars and Global Commerce
- (10th theme)

### Key design decisions (agreed)
- Seed: representative sample of titles (every 3rd article), not full corpus
- Themes: lean fields only at seed time; key_facts/subtopic_details generated on-demand
- Assignments: Haiku in batches of 50 (not Sonnet — cheaper, faster, sufficient)
- Evolution: nudge model — detect candidates, show banner, user applies manually
- Reset: full wipe of all 3 tables + re-seed

### What still needs doing
- Wire /api/kt/tag-new into the VPS scheduler (runs after each sync automatically)
- key_facts/subtopic_details: currently empty in seeded themes — generated on-demand via existing /api/kt/generate when user clicks a theme. Consider pre-populating in background.
- Economist chart capture (see spec below) — next major feature


## Key Themes — Design Spec

### Layout
- Mode switcher row between server bar and tally bar: [News Feed] [Key Themes] — two large full-width toggle buttons
- Key Themes replaces the entire area below the switcher (nav tabs + feed + sidebar hidden)
- News Feed shows current layout unchanged

### Theme grid
- 10 themes in a 5x2 icon grid — Claude-generated names, emoji icons, article counts
- Click a theme: selected card goes dark, all others dim to 30% opacity, downward arrow indicator
- Below grid: bold divider line, then theme detail section

### Theme detail sections (in order)
1. Eyebrow + title + meta (article count, sources, most recent date)
2. Short brief / Full intelligence brief buttons (amber primary)
3. AI Overview — cream panel with amber left border, generated from all theme articles
4. Key Facts — 10 cards in 5x2 grid, two-tone (cream top: number+title; white bottom: body text with bold stats)
5. Sub-topics — pill tags; click opens inline AI overview panel (dark header, bullet points, source badges)
6. Article grid — 2 columns, source/date/title/summary/tags/link per card, sort dropdown

### Briefs
- Short brief: 1-page PDF — executive summary (amber panel) + key developments (bullets) + implications + watch list + source badges
- Full intelligence brief: 4-page PDF — contents table, sections per sub-topic with prose, pull quotes, charts, source citations
- Both pull from: feed articles + newsletters + interviews
- Chart selection: two-pass process — generate brief text first, then score each candidate chart description against brief text, include only charts with meaningful term overlap

## Build History
### 30 March 2026 (Session 25)
- Built KT incremental architecture end-to-end in server.py (tables + 6 routes), deployed to VPS ✅
- meridian.html: renderKeyThemes() patched to call loadThemes(), generateThemes() replaced with DB-backed version, button fixed, localStorage removed
- meridian.html: JS syntax error preventing script from loading beyond char ~116k — NOT YET FIXED
- Investigated Economist chart/map capture — FULLY FEASIBLE:
  - Charts are static PNGs in <figure> elements with <figcaption> "Chart: The Economist" / "Map: The Economist"
  - Playwright element.screenshot() captures them cleanly (confirmed on Iran article, 4 figures)
  - Image src URLs available directly from CDN (content-assets/images/*.png)
  - Designed article_images DB table and two-pass brief relevance selection logic
- Cleaned up temp files and old patch files from repo

### 30 March 2026 (Session 24)
- Key Themes: async generation fixed (job polling pattern for kt/generate and kt/brief)
- Key Themes: article grid raised from 20 to 100, sort fixed
- Key Themes: title-matching, interviews included, PDF print button added
- Key Themes: fact card title boxes fixed to consistent height (68px, bottom-aligned)
- pub_date normalisation: 167 Mac DB rows fixed
- Designed incremental Key Themes architecture

### 30 March 2026 (Session 23)
- Fixed Key Themes end-to-end: generateThemes() and generateBrief() route through Flask
- Async job pattern confirmed working for long Anthropic API calls
- Key Themes confirmed working: 10 themes from 483 articles ✅

### 29 March 2026 (Session 22)
- Designed and built Key Themes feature end-to-end
- Folder tab switcher, theme grid, theme detail, brief modal
- Added /api/kt/generate and /api/kt/brief to server.py

### 29 March 2026 (Session 21)
- Added tally bar and expanded activity bar to 5 sources
- Confirmed autonomous workflow

### 29 March 2026 (Session 20)
- Fixed junk URL filter bug
- Raised article feed limit to 500
- Added autonomous verification pattern

### 29 March 2026 (Session 19)
- Economist scraper: two-step pull (bookmarks + homepage agent picks)
- Recovered 246 Economist bookmark articles after accidental deletion

### 29 March 2026 (Session 18)
- Economist junk filter improved
- Push logic fixed for wake_and_sync.sh
- Documented autonomous mode setup

### 28 March 2026 (Session 17)
- Fixed Mac→VPS sync: push-articles endpoint + wake_and_sync.sh

### 28 March 2026 (Session 16)
- Newsletters fixed on VPS (nginx config)
- score_and_autosave_new_articles() added

### 28 March 2026 (Session 15)
- Shell endpoint added (autonomous deployment unlocked)
- Mobile PWA gap fixed

### 28 March 2026 (Session 14)
- Mobile PWA overhaul
- Economist pub_date fixes
- enrich_title_only_articles() fixed for headless=False

### 28 March 2026 (Session 13)
- Economist scraper completely overhauled

### 28 March 2026 (Sessions 12-8)
- Auto badge, curation filter, agent feedback
- VPS scheduler, Bloomberg clip button
- iPad PWA, autonomous reading agent

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
2. Run the session start health check via shell endpoint once Flask is confirmed up
3. Report health check results before asking what to work on
4. The health check should now include /api/kt/status to show KT seed state
