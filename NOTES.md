# Meridian — Technical Notes
Last updated: 26 March 2026 (Session 3)

## Overview
Personal news aggregator running locally on MacBook Air M1.
Scrapes FT, Economist, Foreign Affairs. Stores in SQLite. Web UI with AI analysis.

## File Locations
- ~/meridian-server/server.py         — Flask API (port 4242)
- ~/meridian-server/meridian.html     — Main frontend
- ~/meridian-server/settings.html     — Cookie management
- ~/meridian-server/meridian.db       — SQLite database
- ~/meridian-server/credentials.json  — Anthropic API key
- ~/meridian-server/cookies.json      — Publication session cookies
- ~/meridian-server/meridian_sync.py  — Background sync script
- ~/meridian-server/newsletter_sync.py — iCloud IMAP newsletter poller
- ~/meridian-server/extension/        — Chrome extension v1.3
- ~/meridian-server/logs/             — Server and sync logs
- ~/meridian-server/younger_economist.wav — 1.1GB recorded audio (mostly silent after 2 mins — see below)
- ~/Library/LaunchAgents/com.alexdakers.meridian.plist       — Auto-start Flask server
- ~/Library/LaunchAgents/com.alexdakers.meridian.http.plist  — Auto-start HTTP server
- ~/Library/LaunchAgents/com.alexdakers.meridian.sync.plist  — Auto-start sync

## Daily Use
Both servers auto-start on login via launchd. Just open:
http://localhost:8080/meridian.html

If server is down, check with: curl http://localhost:4242/api/health
To restart Flask: launchctl unload ~/Library/LaunchAgents/com.alexdakers.meridian.plist && launchctl load ~/Library/LaunchAgents/com.alexdakers.meridian.plist
To restart HTTP: launchctl unload ~/Library/LaunchAgents/com.alexdakers.meridian.http.plist && launchctl load ~/Library/LaunchAgents/com.alexdakers.meridian.http.plist

## Database (26 March 2026)
Total: ~272 articles
- Financial Times: 116 (115 full_text)
- The Economist: 86 (all full_text)
- Foreign Affairs: 31 (all full_text)
Status: ~269 full_text

## Syncing
FT: Auto-syncs every 6h via launchd using Playwright + persistent profile (ft_profile/)
Economist: Auto-syncs every 6h via launchd using Playwright + persistent profile
Foreign Affairs: Auto-syncs every 6h via launchd using Playwright + fa_profile/
All quiet hours 1-6am.

## Newsletter Pipeline
- iCloud alias: meridian.newsletters@icloud.com
- Gmail auto-forwards from noreply@news.bloomberg.com and bloomberg@mail.bloomberg.com
- newsletter_sync.py polls iCloud IMAP (alex.dakers@icloud.com, app-specific password)
- iCloud IMAP: host=imap.mail.me.com, port=993, auth with primary address not alias
- iCloud requires BODY[] not RFC822 for fetch
- App-specific password stored in newsletter_sync.py
- Stores in newsletters DB table: source, subject, body_html, body_text, received_at
- Flask route: /api/newsletters/sync (POST)
- 🔄 Newsletters button in header triggers manual sync
- renderNewsletters() fetches from /newsletters API, renders HTML in iframe on click
- Newsletter tab showing 0 as of 26 Mar — trigger manual sync with:
  curl -s http://localhost:4242/api/newsletters/sync -X POST

## Video Transcript Pipeline (installed 25 March 2026)
Tools installed:
- Homebrew: /opt/homebrew/bin/brew
- yt-dlp: ~/Library/Python/3.9/bin/yt-dlp (not on PATH — use full path)
- ffmpeg: installed via brew (required by Whisper)
- sox: installed via brew (audio recording)
- blackhole-2ch 0.6.1: virtual audio driver (requires reboot after install)
- openai-whisper 20240930: ~/Library/Python/3.9/bin/whisper
- Whisper models cached at: ~/.cache/whisper (small: 461MB, medium: 1.42GB)

### yt-dlp approach (preferred — fast, automatic):
Works for ~90% of YouTube videos. Fails with HTTP 403 on protected/new content.
```
~/Library/Python/3.9/bin/yt-dlp -f 140 --cookies-from-browser chrome \
  -o "~/meridian-server/output.m4a" "YOUTUBE_URL"
```

### BlackHole approach (fallback for protected content):
1. System Preferences → Sound → Output → select Multi-Output Device
   (Must be set here, not just Audio MIDI Setup — reboot required after first install)
2. Volume keys disabled with Multi-Output Device — use in-player volume control
3. Record: sox -t coreaudio "BlackHole 2ch" ~/meridian-server/output.wav
4. Verify BEFORE full recording: sox output.wav -n stat 2>&1 — check Maximum amplitude non-zero
5. Transcribe: ~/Library/Python/3.9/bin/whisper output.wav --model small --language en --output_dir ~/meridian-server/ --output_format txt --verbose True

### Known issue — Economist site DRM:
- Economist video player appears to use protected audio routing
- BlackHole captures first ~2 mins (ads/intro) then goes silent for main content
- YouTube version of same video works fine with BlackHole
- Workaround: use Chrome DevTools Network tab to find direct .mp4 URL, download with curl
- younger_economist.wav (1.1GB) is mostly silent — can delete when done

### Whisper notes:
- FP16 warning on CPU is harmless
- Use --model small (faster, reliable) not medium (slower, stopped early on Python 3.9)
- Whisper hallucinates "U.S. Army" repeatedly over silent audio — sign of bad recording
- tiny model ~5 mins, small ~10-15 mins, medium ~20+ mins for 45-min audio

### Target interview:
- Sir Alex Younger (former MI6 chief, 2014-2020) on Iran war
- Economist YouTube: https://www.youtube.com/watch?v=Lggjw3OuFrw (10 min, protected)
- Economist site: https://www.economist.com/insider/inside-defence/a-former-spy-chiefs-take-on-intelligence-and-the-iran-war (45 min, DRM protected)
- ✅ DONE — transcript at ~/meridian-server/younger_interview.txt (7,740 words, 44m 57s, clean)

## Planned Features
### Interviews & Briefings tab
- New tab in Meridian for video/audio interview transcripts
- DB table: interviews (id, title, url, published_date, added_date, duration_seconds, transcript, summary, source, status, thumbnail_url)
- Status states: pending / needs_recording / transcribed / summarised
- Flow: paste YouTube URL → yt-dlp auto-attempt → if 403, flag as "needs_recording" with sox instructions → Whisper → Claude summary → saved to DB
- Auto-fetch YouTube title/thumbnail on URL paste
- UI: expandable transcript + summary per item

### Suggested Articles tab
- Daily snapshot of most-read/trending from Economist, FT, Foreign Affairs
- Runs once per day via scheduler
- DB table: suggested_articles (id, title, url, source, snapshot_date, summary)
- Builds historical archive — browse back by date
- UI: separate tab with date picker

### Other carry-forward
- Git repo for server.py backup
- Ask AI standalone freeform button
- Newsletter tab showing 0 — check iCloud IMAP sync

## How to start servers manually (if launchd fails)
Tab 1: python3 ~/meridian-server/server.py
Tab 2: cd ~/meridian-server && python3 -m http.server 8080
Then open: http://localhost:8080/meridian.html

## Build History

### 24 March 2026
- FT sync completely overhauled: persistent Playwright profile (ft_profile/), correct SAVED_URL, 90s manual login window
- FT early-exit: stops scraping when first known article found
- FT pub_date: extracted from time[datetime] on article page, backfilled for 43 existing articles
- Economist Load more: now clicks button, early-exit on known articles
- Economist full text selector fixed: p[data-component="paragraph"]
- Economist 7 new articles fetched and enriched manually
- Sync Now replaced with per-source sync buttons (🔄 FT, 🔄 Eco, 🔄 FA)
- Foreign Affairs scraper added: ForeignAffairsScraper with fa_profile/, 120s login window
- Foreign Affairs first sync: 30 articles, all full_text and AI enriched
- DB: FT 87→137, Economist 76→83, FA 1→31

### 17 March 2026
- AI Analysis Panel: fuzzy dedup for presets, dynamic presets from top tags, amber progress bar
- PDF briefing: fixed bold, A4 print CSS, no URLs printed
- Article feed: status filter, batch open, delete/bulk delete, sort by pub_date
- Chrome extension: clips pub_date, passes status on save
- Server: fixed db() locking bug, enrich_with_ai → enrich_article_with_ai, pub_date column added

### 19 March 2026
- Newsletter tab added to nav
- Bloomberg Auto-clip button added
- Settings page added (settings.html)
- 24h activity bar added

### 20 March 2026
- HTTP server launchd plist added
- Bloomberg API response format confirmed: HAL format, data._embedded.items[].metadata.{url, headline.text}
- New Anthropic API key stored in credentials.json
- AI analysis confirmed working
- meridian_smtp.py created, newsletter approach switched to RSS/IMAP

### 25 March 2026
- FA pub_date fixed: span.topper__date selector, all 31 articles backfilled
- Economist pub_date: extracted from URL pattern /YYYY/MM/DD/, all 86 backfilled
- Economist auto-clip added: fetch_economist_article_text called during sync
- Removed cookie-based bookmarks sync entirely
- Bloomberg removed from all code (articles kept in DB)
- Newsletter pipeline complete: iCloud IMAP, newsletter_sync.py, renderNewsletters()
- Newsletter tab UI: preview → click → full HTML iframe

### 26 March 2026
- Video transcript pipeline research and tooling installed (see above)
- Economist interview recording attempted — DRM issue, mostly silent
- NOTES.md updated with full transcript pipeline documentation

### Economist Interview Transcription — Confirmed Workflow (26 March 2026)
Tested on: Sir Alex Younger interview (44m 57s, insider/inside-defence)

1. Open article in Chrome, start playing the video
2. DevTools → Network tab → filter "mp4"
3. Look for rendition.m3u8?fastly_token=... request (type: xhr)
4. Right-click → Copy URL — do this quickly, token expires
5. Download: ~/Library/Python/3.9/bin/yt-dlp "M3U8_URL" -o ~/meridian-server/interview.mp4
6. Convert: ffmpeg -i interview.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 interview.wav
7. Transcribe: ~/Library/Python/3.9/bin/whisper interview.wav --model small --language en --output_dir ~/meridian-server/ --output_format txt --verbose True

Notes:
- BlackHole/sox fails (DRM silences after 2 mins) — yt-dlp m3u8 approach is the fix
- Use --model small (tiny: faster but less accurate, medium: stalled on Python 3.9)
- younger_economist.wav (1.1GB) is the failed BlackHole recording — safe to delete
- younger_interview.mp4 + .wav + .txt are the good files

## Current Status (end of 26 March session)
- younger_interview.txt: complete 44m 57s transcript, 7,740 words, clean
- younger_economist.wav: 1.1GB failed BlackHole recording — DELETE THIS
- Next: build Interviews & Briefings tab in Meridian to store/display transcripts
- DB table needed: interviews (id, title, url, published_date, added_date, duration_seconds, transcript, summary, source, status, thumbnail_url)
- Status states: pending / needs_recording / transcribed / summarised
- First entry will be: Sir Alex Younger, Inside Defence, Economist, 26 Mar 2026

### 26 March 2026 (Session 2)
- Interviews & Briefings tab built and live
- DB table: interviews (id, title, url, source, published_date, added_date, duration_seconds, transcript, summary, speaker_bio, status, thumbnail_url)
- Status states: pending / needs_recording / transcribed / summarised
- Flask routes: GET /api/interviews, POST /api/interviews, PATCH /api/interviews/<id>, DELETE /api/interviews/<id>, POST /api/interviews/fetch-meta
- UI: tab after Newsletters, feed-style cards with thumbnail, status pill, word count
- Detail view: thumbnail + speaker bio side by side, summary box, scrollable transcript
- YouTube URL paste → auto-fetches title + thumbnail via oEmbed (no API key needed)
- Bio auto-generated by Claude on save for all future interviews
- Summary generated on demand via ✦ Generate summary button → saves to DB, updates status to summarised
- First entry: Sir Alex Younger, Inside Defence, Economist, 44m 57s, 7,740 words, summarised
- younger_economist.wav (1.1GB failed BlackHole recording) — safe to delete

### 26 March 2026 (Session 3)

## Suggested Articles — full rebuild
- DB schema: added status (new/reviewed/saved/dismissed) + reviewed_at columns
- save_suggested_snapshot: upsert instead of delete+replace — no duplicates, accumulates over time
- GET /api/suggested: now accepts since= (date filter) and status= params, returns new_count + last_added_ts
- PATCH /api/suggested/<id>: update status + reviewed_at
- POST /api/suggested/bulk-delete: delete list of IDs
- GET /api/suggested/status: returns {running: bool} for polling
- FT/Economist scoring: now uses Claude instead of keyword match — same quality as web search results
- UI: time filters (all/24h/7d/30d/custom date), status filter (all/new/reviewed/saved/dismissed)
- UI: checkbox on each card, bulk bar (select all, mark as new, dismiss, delete with confirm)
- UI: NEW/reviewed/dismissed status pills on each card
- UI: opening article marks as reviewed immediately (pill updates in place, badge decrements)
- UI: dismiss button per card, fades card to 0.4 opacity
- UI: polling refresh (3s interval vs /api/suggested/status) replaces fixed 50s wait
- UI: auto-refresh on tab open if last added_at > 24h ago
- Nav badge shows new-count only (not total)
- All existing suggested articles migrated: status defaulted to 'new'

## Interviews & Briefings tab
- DB table: interviews (id, title, url, source, published_date, added_date, duration_seconds, transcript, summary, speaker_bio, status, thumbnail_url)
- Flask routes: GET /api/interviews, POST /api/interviews, PATCH /api/interviews/<id>, DELETE /api/interviews/<id>, POST /api/interviews/fetch-meta
- UI: tab after Newsletters, feed-style cards, detail view with thumbnail + speaker bio side by side
- Speaker bio auto-generated by Claude on save for all future interviews
- Summary generated on demand via ✦ Generate summary button → saves to DB, status → summarised
- First entry: Sir Alex Younger, Inside Defence, Economist, 44m 57s, 7,740 words, summarised
- younger_economist.wav (1.1GB failed BlackHole recording) — safe to delete

## Suggested Articles tab
- DB table: suggested_articles (id, title, url, source, snapshot_date, score, reason, added_at)
- Flask routes: GET /api/suggested, POST /api/suggested/refresh
- Claude web search (claude-sonnet-4-20250514 + web_search_20250305 tool) finds trending articles
- Agentic loop handles multi-turn web search (up to 6 attempts)
- Scores articles 0-10 against user's interest profile (built from saved article topics/tags)
- Only returns articles scoring 6+ that aren't already saved
- UI: tab after Interviews, cards with ★ score, ↗ Open article + Save to Feed buttons
- Refresh button triggers new search (~45 seconds), date picker to browse history
- 14 articles returned on first run, all highly relevant

## AI Analysis
- Now includes interviews in context (summary + transcript excerpt)
- Thinking step shows article + interview count

## Other improvements
- Sync all button (amber) fires all 3 scrapers in parallel, polls status, auto-refreshes feed when done
- FT sync warning only shows on actual error (not on 0 new articles)

## Follow-up items for next session
- Economist suggested articles sourcing: currently scrapes homepage (editorial picks) not strict most-read — consider better signal
- Autonomous reading agent: learn from saved articles, auto-save high-scoring articles to Feed with provenance flag
  - Richer interest profile from 276 saved articles
  - Playwright browses FT/Economist/FA using existing logged-in profiles
  - Auto-save if score ≥ 8, review queue for 6-7
  - Feedback loop: deletes down-weight, reads up-weight
  - Suggested tab becomes review queue for borderline articles

## Suggested Articles — source improvements (26 Mar session 3 continued)
- FT: switched from ft.com/most-read (returns 0 headless) to ft.com homepage — now returns 8 articles
- Economist: scrapes most-read page via Playwright, then falls back to homepage — intermittent (0-4 articles)
- Claude web search: now searches FA + general quality sources (Foreign Policy, CFR, Atlantic Council etc.)
- Domain filter removed — all quality sources welcome
- Merging: Playwright results scored by keyword match (simple, needs improvement)

## Known issues / next session
- FT articles scored by keyword match only — pulls irrelevant articles at score 6
  Fix: pass FT/Economist titles through Claude for proper interest scoring
- Economist Playwright intermittent — selector needs hardening
- Suggested tab: refresh button waits fixed 50s — should poll status instead
- Economist suggested sourcing: consider economist.com/latest or section pages
- Time period clarity: FT=homepage featured, Economist=most-read page, Claude=last 7 days

## Autonomous reading agent (planned — next session)
- Learn from saved articles, auto-save high-scoring to Feed with provenance flag
- Richer interest profile from saved article topics/tags/authors
- Playwright browses FT/Economist/FA using existing logged-in profiles
- Auto-save if score ≥ 8, review queue for 6-7
- Feedback loop: deletes down-weight, reads up-weight
- Suggested tab becomes review queue for borderline articles
- Settings: auto-save threshold, max per sync, sources

## Title-only enrichment (added session 4)
- enrich_title_only_articles() — fetches full text for all title_only articles
- FT/Economist: uses logged-in Playwright profiles (ft_profile, economist_profile)
- Foreign Affairs: uses fa_profile
- Other sources (CNN, Atlantic Council, CFR etc): generic BeautifulSoup scrape, no login
- _save_enriched_article() saves enriched fields back to DB after AI enrichment
- Routes: POST /api/enrich-title-only, GET /api/enrich-title-only/status
- Embedded in Sync All: runs automatically after all 3 scrapers finish
- FT title_only articles: picked up by next regular FT sync if Playwright headless fails

## Suggested Articles — known issues for next session
1. FT articles scoring 6 — keyword matching too simple, pulling in unrelated articles (Meta/Google, Democrat election etc). Need to pass FT/Economist titles through Claude for proper interest scoring, same as web search results.
2. Economist Playwright inconsistent — returns 4 articles sometimes, 0 others. Selector needs hardening, possibly try economist.com/latest or section pages as fallback.
Both are refinements for next session. Core is working well — good source diversity, relevant content, save to feed button works.
