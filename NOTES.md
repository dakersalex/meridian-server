# Meridian — Technical Notes
Last updated: 28 March 2026 (Session 12)

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

## Next Steps
1. Economist scraper intermittency — Cloudflare blocking VPS, works on Mac but inconsistent
   Fix: improve selector resilience, handle Just a moment... challenge page gracefully
2. PWA icons — proper 192×192 and 512×512 instead of placeholders
3. Bloomberg enrichment — manual via Chrome extension
4. Terminal output visibility — need a better pattern so Claude can read output without pasting

## Build History
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
