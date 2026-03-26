# Meridian — Technical Notes
Last updated: 26 March 2026

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
- Next attempt: Chrome DevTools Network tab → find .mp4 URL → curl download

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
- Fix Bloomberg sync (pagination broken — API returns empty _embedded)
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
