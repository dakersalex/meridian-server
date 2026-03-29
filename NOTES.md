# Meridian — Technical Notes
Last updated: 29 March 2026 (Session 22 — complete)

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

## Database (28 March 2026)
Total: ~299 articles
- Financial Times: 122
- The Economist: 86
- Foreign Affairs: 42
- Bloomberg: 39
- Other (CNN, Atlantic Council, Foreign Policy, CFR): ~10

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
1. Run in Terminal: `cat ~/meridian-server/NOTES.md | pbcopy`
2. Open claude.ai in Chrome and start a new chat
3. Paste NOTES.md contents into the chat
4. **Click the Claude in Chrome extension icon in the Chrome toolbar**
   (red/orange asterisk icon, right of the address bar)
5. **Click Connect in the popup** — this links the extension to this conversation
   ⚠️ This step is required every new chat — without it Claude cannot run shell commands or deploy code
6. The extension opens an MCP tab group (orange-outlined tabs labelled ✅ Claude (MCP))
7. Claude runs the session start health check automatically and confirms it is ready

**Claude should prompt the user at session start:**
> "Please click Connect on the Claude in Chrome extension (red/orange asterisk icon in your Chrome toolbar) if you haven't already — I need it to deploy code and run commands autonomously."

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
6. Report the confirmed result to the user — never say “please check” or “please refresh”

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
- Check the API to confirm if it’s a data issue vs cache issue
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
  echo '=== Last log ===' && tail -3 ~/meridian-server/logs/server.log
`).then(d => console.log('HEALTH:', d.stdout));
```
This gives immediate awareness of: Flask status, DB counts, pending enrichments, last sync.

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
- **VPS DB itself** — has all articles ever pushed from Mac (~468 articles)

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

## Next Steps
1. **Key Themes JS routing fix** — generateThemes() and generateBrief() still call api.anthropic.com directly. Replace with SERVER + /api/kt/generate and SERVER + /api/kt/brief. Flask routes already in server.py. Do this FIRST.
2. PWA icons — proper 192×192 and 512×512 instead of placeholders
2. Newsletter auto-sync — newsletter_sync.py is gitignored (has credentials), so VPS can’t auto-sync.
3. **Key Themes feature** — fully designed, ready to build. See design spec below.

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
   - JS auto-sizing: shared font size for all titles (max 2 lines), shared font size for all body text (max 3 lines)
   - JS height equalisation: all tops same height, all bottoms same height
5. Sub-topics — pill tags; click opens inline AI overview panel (dark header, bullet points, source badges)
   - Article grid below filters to that sub-topic when panel is open
6. Article grid — 2 columns, source/date/title/summary/tags/link per card, sort dropdown

### Briefs
- Short brief: 1-page PDF — executive summary (amber panel) + key developments (bullets) + implications + watch list + source badges
- Full intelligence brief: 4-page PDF — contents table, sections per sub-topic with prose, pull quotes, AI-generated charts from article statistics, source article citations
- Both pull from: feed articles (441 with summaries) + newsletters (28) + interviews (1)
- Graphics: AI-generated charts from statistics in article text — NOT scraped images
  - Playwright image capture tested and rejected: figures on FT/Economist are editorial photos not data charts
  - Actual data charts are D3/JS components, not capturable as static images

### Theme generation
- Single Claude API call over all article titles + tags → 10 themes with: name, emoji, keywords, overview paragraph, 10 key facts, sub-topics
- Cached in localStorage under key 'meridian_themes_v1'
- Regenerate button triggers fresh generation
- Article matching: each article matched to theme by comparing its tags against theme keywords

## Build History
### 29 March 2026 (Session 22)
- Designed and built Key Themes feature end-to-end
- Folder tab switcher: News Feed (orange, raised) / Key Themes (recessed behind) with continuous dark ink divider line
- Switcher inserted between masthead and server bar — CSS uses border-bottom on #folder-switcher, active tab uses matching border-bottom colour to erase the line beneath it
- Key Themes JS: switchMode(), renderKeyThemes(), renderThemeGrid(), selectTheme(), renderThemeDetail(), renderSubtopicDetail(), toggleSubtopic(), generateThemes(), generateBrief(), generateBrief()
- Theme grid: 5x2, emoji+name+article count, click selects/dims others, downward arrow indicator
- Theme detail: eyebrow, title, meta, Short Brief / Full Brief buttons, AI Overview panel, Key Facts 5x2 grid, sub-topics pills with dark inline panel, article grid with sort
- Brief modal: amber exec summary panel, markdown-to-HTML rendering
- Themes cached in localStorage('meridian_themes_v1'), Regenerate button clears it
- Article drill-down: clicking article in Key Themes switches back to News Feed and opens it
- Added /api/kt/generate and /api/kt/brief to server.py — both use call_anthropic() server-side
- INCOMPLETE: JS still calls api.anthropic.com directly — Flask routing patch did not apply due to Filesystem MCP instability and extension blocking shell output. Fix next session.
- Tooling issues this session: Filesystem MCP went down twice; Chrome extension blocked shell output containing certain keywords (folder, fetch etc)

### 29 March 2026 (Session 21)
- Added tally bar below nav tabs: My saves / AI picks / Total (hidden on mobile)
- Expanded activity bar from 2 sources (FT, Economist) to 5 (FT, Economist, FA, Bloomberg, FP)
- Both bars populated by updateActivityBar() which runs on load and every 5 minutes
- Browser localStorage caching requires `localStorage.clear() + SW unregister + reload` to pick up new HTML — now done autonomously via javascript_tool on the meridianreader.com MCP tab
- Confirmed autonomous workflow: verify by querying DOM/API → fix → screenshot confirm, no user input needed
- Enrichment progress: 246 title_only Economist bookmarks being enriched in background (~10s/article)

### 29 March 2026 (Session 20)
- Fixed junk URL filter bug: was calling is_junk(url, url) so title prefix checks never ran
- Raised article feed limit from 200 to 500 to prevent bookmarks being cut off
- Persistent Cuba article traced to browser localStorage cache (not DB) — fixed by clearing localStorage via JS autonomously
- Lesson: verify issues by querying DOM/API directly rather than asking user to check
- Added autonomous verification pattern: check DOM → check API → fix → screenshot confirm

### 29 March 2026 (Session 19)
- Economist scraper: switched to two-step pull (bookmarks = auto_saved=0, homepage agent picks = auto_saved=1 scored >=8)
- Fixed Economist bookmark title extraction: <a> is inside <h3> so anchor text IS the title
- Added section label blocklist (Finance & economics, Schumpeter etc.) to prevent column names being saved as titles
- Added URL junk filter (/podcasts/, /newsletters/, /films/ etc.)
- Accidentally deleted all Economist articles (auto_saved=0) assuming they were homepage scrapes
- Wrote recover_economist_bookmarks.py to re-scrape full bookmarks page with Load More
- Recovered 246 real bookmark articles (+ 4 agent picks) and pushed all 250 to VPS
- Score window widened 24h -> 48h in score_and_autosave_new_articles to prevent articles falling through gap
- Mac Flask restart: kill PID + launchctl load (pkill pattern didn't match)
- Cleaned wipe_vps_economist.py helper script (scp to VPS and run)

### 29 March 2026 (Session 18)
- Economist junk filter: added prefix blocklist for newsletter digests (War Room, Blighty, US in Brief, Espresso etc.)
- Push logic fixed: wake_and_sync.sh now only pushes FA (all) + FT/Economist auto_saved=1 to VPS
- Cleaned up 5 junk Economist newsletter articles already on VPS
- Documented autonomous mode setup in NOTES.md (Claude in Chrome + shell endpoint + Meridian tab)

### 28 March 2026 (Session 17)
- Root cause: Mac-scraped articles go to Mac DB only; VPS has separate DB and never saw them
- Fix: added POST /api/push-articles endpoint — receives batch of articles, upserts them, triggers scoring
- Fix: wake_and_sync.sh now pushes articles saved in last 3h to VPS after every sync
- Manual backfill: pushed 22 articles (FT/Economist/FA last 24h) to VPS immediately
- VPS now has Economist articles up to 27 Mar; will have 28 Mar after next Mac sync at 17:40 CEST
- Auto-scoring ran on push: 9/20 + 2/11 articles auto-saved with ✔ Auto badge
- Good scores: Autonomous swarms (8), Growing divide America/Israel (9), Christine Lagarde (8), Stocks slump (9)

### 28 March 2026 (Session 16)
- Newsletters fixed: added /newsletters location block to nginx on VPS (was 404 — only /api/ was proxied)
- Auto-tagged FT/Economist articles fixed: added score_and_autosave_new_articles() function
  - Scores recently-added FT/Economist articles from main articles table (not just suggested_articles)
  - Runs automatically after every Mac Sync All via _enrich_after_sync()
  - Uses claude-haiku in batches of 20, marks best articles (score ≥8) as auto_saved=1
  - New route: POST /api/agent/score-new?hours=N for manual backfill
  - Backfill run: 23/45 FT/Economist articles from last 7 days auto-saved
- Economist filter: confirmed working — 85/86 articles in frontend with correct dates

### 28 March 2026 (Session 15)
- Shell endpoint added to server.py: POST /api/dev/shell (localhost only) — Claude can deploy autonomously
- Mobile PWA gap fixed: clean rewrite of mobile CSS, removed all conflicting rules
- Pull-to-refresh removed entirely (was causing layout gap)
- Mobile filter bar added below nav tabs: Source / Time period / Curation
- iPhone masthead fix: tagline+date hidden, flex-wrap:nowrap
- Debug overlay removed
- feed-header-outer: filters moved outside feed-area in HTML to avoid layout-flow gap

### 28 March 2026 (Session 14)
- Mobile PWA overhaul: fixed header using `position: fixed` (not sticky — Safari iPad bug)
- `pointer: coarse` media query targets touch devices regardless of screen size/orientation
- Activity bar hidden on mobile; compact 🔄 Sync button added to server bar instead
- + Add Article button hidden on mobile (reading-focused use case)
- Pull-to-refresh gesture implemented (touchstart/move/end, 60px threshold)
- Service worker updated: always network-first for meridian.html (never serve stale)
- Service worker cache bumped to v4
- Economist pub_date fixes: 24 articles corrected using URL regex `/YYYY/MM/DD/`
- AI enrichment fixed: no longer overwrites URL-extracted pub_dates
- enrich_title_only_articles() fixed: now uses headless=False for Economist (was headless=True → 0/19 enriched)
- Breakpoint: `@media (max-width: 1400px) and (pointer: coarse)` — catches iPhone + iPad all orientations
- Mobile typography improvements: larger titles, better line-height, safe-area padding
- Modals slide up from bottom on mobile (iOS sheet style)

### 28 March 2026 (Session 13)
- Economist scraper completely overhauled: switched from bookmarks to homepage scraping
- headless=False added to bypass Cloudflare challenge page
- economist_profile/ persistent session (no daily login needed)
- Claude title scoring added BEFORE fetching any articles: collect titles → score → only open articles scoring 6+
- Explicit scoring bands in prompt (8-10 geopolitics/finance, 5-7 business/tech, 0-4 lifestyle/health/science)
- Removed early-exit on first existing article: now checks ALL homepage articles for new ones
- Articles saved as title_only (not fetched inline), enriched by enrich_title_only_articles() on next Mac sync
- call_anthropic() fixed: ensure_ascii=False + encode('utf-8') — fixes 400 errors from curly apostrophes
- Cleaned up ~32 bad Economist articles from DB (section labels, title_only with no body)
- Anthropic API credits exhausted mid-session — Mac API key depleted, VPS unaffected
- Confirmed working end-to-end: 15/21 homepage articles scored 6+, 6 filtered out, 8 saved
- mlog helper confirmed working: mlog <command> writes output to vps_last_log.txt for Claude to read

### 28 March 2026 (Session 12)
- Auto badge (✦ Auto orange pill) on agent-saved articles — implemented and live
- Curation filter (All / My saves / AI suggested) in Feed — implemented and live
- Delete feedback toast for AI-saved articles — implemented and live
- Suggested refresh + agent added to VPS scheduler (runs every 6h automatically, Mac not required)
- sync_now.py and meridian_sync.py now call enrich_title_only_articles() after sync
- Activity bar cleaned up: removed individual FT/Economist/FA/Newsletters/Reload buttons
- Suggested tab: ↻ Refresh renamed to 🔍 Find Articles, Run Agent button removed
- VPS credentials.json updated with correct Anthropic API key (was expired/truncated)
- Suggested URL dedup fixed: normalise_url() strips query params before dedup check
- Missing pub_date on suggested cards now shows today's date as fallback
- vps_last_log.txt added to .gitignore
- Terminal bracket paste mode fixed: printf '\e[?2004l'
- Diagnosed VPS log reading pattern: ssh root@... "journalctl -u meridian --since '10 minutes ago'" > ~/meridian-server/vps_last_log.txt

### 27 March 2026 (Session 11)
- Investigated auto_saved badge issue: confirmed auto_saved=0 in all frontend article objects, status=agent=1 (1 article). Root cause: auto_saved not mapped in loadFromServer()
- Bloomberg clip button deployed and verified
- Three features (auto badge, curation filter, delete feedback) diagnosed and fully specced

### 27 March 2026 (Session 10)
- Auto NOTES.md update: handled directly by Claude via filesystem MCP at session end
- Bloomberg clip button: '📎 Clip Bloomberg (N)' appears in activity bar when Bloomberg title-only articles exist
- updateClipBloombergBtn() hooked into renderAll() so visibility updates automatically

### 27 March 2026 (Session 9)
- Filesystem MCP confirmed working in Claude Desktop — direct file read/write, no more heredoc patches
- Code review: identified 11 issues across server.py
- Credentials caching: load_creds() now checks mtime, avoids 20+ disk reads per scrape
- call_anthropic() shared helper: single place for all Anthropic API calls with 429 retry
- enrich_article_with_ai() refactored to use call_anthropic()
- FT Suggested scoring bug fixed: agentic loop fallback now scores and returns Playwright articles
- syncSource() fixed: replaced 20s fixed wait with proper polling
- Server status panel: now shows 'meridianreader.com · connected'
- deploy.sh created: single command git add/commit/push + SSH pull + systemctl restart
- Economist scraper fixed: login detection, locator() fix, better title extraction
- Bulk status fix: 19 articles incorrectly stuck as title_only — patched to full_text

### 27 March 2026 (Session 8)
- Claude Code installed
- iPad PWA: manifest.json + sw.js created
- ↻ Refresh button added to header
- ✦ Preview button on Suggested cards
- Autonomous reading agent: run_agent(), agent_log, agent_feedback tables
- Playwright VPS migration attempted — VPS IP blocked by FT/FA/Economist, scrapers remain on Mac
- Filesystem MCP server configured in Claude Desktop

### 26 March 2026 (Session 7)
- Purchased meridianreader.com, DNS, SSL via Certbot
- Meridian now live at https://meridianreader.com/meridian.html

### 26 March 2026 (Session 6)
- GitHub repo created, Hetzner VPS provisioned
- Flask migrated to VPS as systemd service, nginx installed

### 26 March 2026 (Sessions 1-5)
- Interviews & Briefings tab, Suggested Articles, Title-only enrichment
- Newsletter pipeline (iCloud IMAP), Bloomberg removed

### 24-25 March 2026
- FT sync overhauled, Economist selector fixed, Foreign Affairs scraper added
- Per-source sync buttons, Sync All, AI Analysis panel

## GitHub Visibility
- Repo is currently PUBLIC: github.com/dakersalex/meridian-server
- No sensitive files in repo (credentials.json, cookies.json, meridian.db excluded)

## Session Starter Prompt
Copy and paste this at the start of each Claude session:

---
You are helping me build and maintain Meridian, my personal news aggregator.
Here are my technical notes with full context:

[PASTE NOTES.md HERE]

The codebase is on GitHub at github.com/dakersalex/meridian-server (public).
The live app runs at https://meridianreader.com/meridian.html

Please review the notes and confirm what we should work on today.
---

**Note for Claude reading this:** At the start of every session you must:
1. Remind the user to click Connect on the Claude in Chrome extension if not already done
2. Run the session start health check once the shell endpoint is reachable
3. Report the health check results before asking what to work on
