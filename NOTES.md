# Meridian — Technical Notes
Last updated: 24 March 2026

## Overview
Personal news aggregator running locally on MacBook Air M1.
Scrapes FT, Economist, Bloomberg. Stores in SQLite. Web UI with AI analysis.

## File Locations
- ~/meridian-server/server.py         — Flask API (port 4242)
- ~/meridian-server/meridian.html     — Main frontend
- ~/meridian-server/settings.html     — Cookie management
- ~/meridian-server/meridian.db       — SQLite database
- ~/meridian-server/credentials.json  — Google OAuth (not used for FT/Economist credentials)
- ~/meridian-server/cookies.json      — Publication session cookies (FT, Economist, Bloomberg)
- ~/meridian-server/meridian_sync.py  — Background sync script
- ~/meridian-server/extension/        — Chrome extension v1.3
- ~/meridian-server/logs/             — Server and sync logs
- ~/Library/LaunchAgents/com.alexdakers.meridian.plist       — Auto-start Flask server
- ~/Library/LaunchAgents/com.alexdakers.meridian.http.plist  — Auto-start HTTP server (added 20 Mar)
- ~/Library/LaunchAgents/com.alexdakers.meridian.sync.plist  — Auto-start sync

## Daily Use
Both servers auto-start on login via launchd. Just open:
http://localhost:8080/meridian.html

FT sync: a browser window will open on first sync — log in if prompted (90s window).
FT profile saved in ~/meridian-server/ft_profile/ — stays logged in between sessions.
Use "Sync Now" button in Meridian to trigger manual sync of all 3 sources.

If server is down, check with: curl http://localhost:4242/api/health
To restart Flask: launchctl unload ~/Library/LaunchAgents/com.alexdakers.meridian.plist && launchctl load ~/Library/LaunchAgents/com.alexdakers.meridian.plist
To restart HTTP: launchctl unload ~/Library/LaunchAgents/com.alexdakers.meridian.http.plist && launchctl load ~/Library/LaunchAgents/com.alexdakers.meridian.http.plist

## Database (24 March 2026)
Total: ~290 articles
- Financial Times: 137 (all full_text, pub_dates backfilled)
- The Economist: 83 (all full_text, all enriched)
- Foreign Affairs: 31 (all full_text — first full sync done today)
- Bloomberg: 39 (37 full_text, 2 fetched — sync still broken)
Status: ~285 full_text, 3 title_only (FT paywalled), 2 fetched (Bloomberg)

## Syncing
FT: Auto-syncs every 6h via launchd using Playwright + credentials in cookies.json
Bloomberg: Auto-syncs every 6h via launchd using Playwright scraper (BloombergScraper)
Economist: Auto-syncs every 6h via launchd using Playwright + persistent profile
All three auto-sync every 6 hours via launchd. Quiet hours 1-6am.

Bloomberg cookies stored in cookies.json under "bbg" key — expire every few weeks.
To refresh: go to bloomberg.com/portal/saved → DevTools Console → type: copy(document.cookie) → paste in settings.html

## Clipping Full Text
Auto-clip FT: Click Auto-clip FT button — opens 5 articles at a time, clips automatically
Auto-clip BBG: Click Auto-clip BBG button — mirrors FT behaviour
Manual: Open any article, click Clip Full Text in extension popup

## Features
- AI analysis panel: 4 themes x 4 bullets + 3 implications, ~600-700 words
- Fixed presets: Weekly digest, Key themes, Markets overview, What am I missing?
- Dynamic presets: top tags from current time window, fuzzy deduped
- Reading progress bar (amber, right edge)
- PDF briefing: A4, ~2 pages, bold preserved, no URLs printed
- Article feed: status filter, batch open, delete, sort by pub_date
- 24h activity bar: new articles per source + last sync time + FT warning
- Settings page: bloomberg.com/settings.html — cookie management for all 3 sources
- Chrome extension v1.3: auto-harvests cookies, clips pub_date, Economist sync button

## Server (server.py) Key Details
- FT sync: uses FTScraper (Playwright + email/password login) via run_sync("ft")
- Bloomberg sync: uses BloombergScraper (Playwright, persistent profile) via run_sync("bloomberg")
- Economist sync: uses EconomistScraper (Playwright, persistent profile) via run_sync("economist")
- run_bookmarks_sync(): cookie-based fallback — uses fetch_bloomberg_api() for BBG, fetch_bookmarks_for_pub() for FT/ECO
- fetch_bloomberg_api(): calls login.bloomberg.com/portal/bookmarks API — response is HAL format: data._embedded.items, each item has metadata.url and metadata.headline.text
- Bloomberg API response format: {"_embedded": {"items": [{id, contentId, savedDate, metadata: {url, headline: {text}, brand, publishedAt}}]}}
- update_article uses direct sqlite3 (fixed db() locking bug)
- enrich_article_with_ai (was enrich_with_ai — do not revert)
- pub_date column exists in articles table
- AI calls proxied through server using credentials.json (Anthropic API key stored separately)
- Junk filter in FTScraper and run_bookmarks_sync

## Bloomberg Sync — Known Issue (20 Mar 2026)
- BloombergScraper (Playwright) only scrapes page 1 of saved articles (~6 articles)
- fetch_bloomberg_api() times out when called from Python directly
- In-browser API call via page.evaluate() returns empty _embedded
- Root cause: Bloomberg API requires browser-level auth that plain Python requests can't replicate
- Next session: inspect the > next page button HTML on bloomberg.com/portal/saved to fix Playwright pagination
- The API response structure is confirmed: data._embedded.items[].metadata.{url, headline.text}

## Known Issues
- Bloomberg sync broken — in-browser API call returns empty _embedded, plain Python requests time out
- Bloomberg cookies expire every few weeks, refresh via settings.html
- FT profile needs manual login once per session if ft_profile/ session expires (90s window given)
- PDF occasionally slightly over 2 pages
- Economist full text extraction now uses p[data-component="paragraph"] selector

## Next Ideas (carry forward)
- Fix Bloomberg sync — in-browser API returns empty _embedded, need to debug auth or try Playwright pagination
- Newsletter tab: use RSS feeds for Substack — renderNewsletters() and Flask /newsletters route exist, need DB population and RSS polling script
- Add Auto-clip for Economist (mirrors FT auto-clip behaviour)
- Mark as read per article
- Settings link in Meridian header
- Stale Bloomberg cookie warning in UI
- 3-page PDF option
- Extension auto-detects source publication
- Article count per topic in sidebar
- Add /api/articles/{id}/enrich endpoint to server.py for on-demand enrichment
- Consider storing full article text: currently body field is overwritten by AI fullSummary during enrichment — raw text is discarded. Options: (a) add a raw_text column to DB, (b) show raw text in detail view alongside AI summary, (c) keep current behaviour. Pros of storing: read full article offline, better AI context. Cons: much larger DB, longer sync times.
- Foreign Affairs sync: fa_profile/ has saved session — trigger via 🔄 FA button or curl. If login needed, use magic link in Playwright window
- Foreign Affairs pub_date fix needed: date format is "March 20, 2026" (not "Published on..."), regex needs updating
- Foreign Affairs articles all showing 24 Mar 2026 (sync date) instead of publication date — backfill script pending

## How to start servers manually (if launchd fails)
Tab 1: python3 ~/meridian-server/server.py
Tab 2: cd ~/meridian-server && python3 -m http.server 8080
Then open: http://localhost:8080/meridian.html

## Build History

### 24 March 2026
- FT sync completely overhauled: persistent Playwright profile (ft_profile/), correct SAVED_URL (myft/saved-articles/...), 90s manual login window
- FT early-exit: stops scraping when first known article found
- FT status fix: articles now correctly set to full_text or title_only after fetch
- FT pub_date: extracted from time[datetime] on article page, backfilled for 43 existing articles
- Economist Load more: now clicks button instead of pressing End key
- Economist early-exit on Load more: checks for known articles after each click
- Economist full text selector fixed: p[data-component="paragraph"] (matches current site structure)
- Economist 7 new articles fetched and enriched manually
- Sync Now button replaced with individual per-source sync buttons (🔄 FT, 🔄 Eco, 🔄 BBG, 🔄 FA)
- Foreign Affairs scraper added: ForeignAffairsScraper with fa_profile/, h3.body-m selector, 120s login window
- Foreign Affairs first sync: 30 articles, all full_text and AI enriched
- FA login: uses magic link (Sign In Without Password) pasted into Playwright window
- DB: FT 87→137, Economist 76→83, FA 1→31, all now full_text
- Bloomberg sync still broken (API returns empty) — next session

## Build History

### 17 March 2026
- AI Analysis Panel: fuzzy dedup for presets (6-char prefix), dynamic presets from top tags, auto-scroll suppressed, amber progress bar (3px right edge)
- PDF briefing: fixed bold (innerText → innerHTML), stripped ## markers, A4 print CSS, no URLs printed
- Article feed: status filter, article counter, batch open (5 at a time), delete/bulk delete, data-id attributes, sort by pub_date with saved_at fallback
- Chrome extension: clips pub_date, passes status on save
- Server: fixed db() locking bug (direct sqlite3), enrich_with_ai → enrich_article_with_ai, pub_date column added, AI topic prompt with category list
- Data: Bloomberg empty-body articles → title_only, Foreign Affairs test article removed

### 19 March 2026
- Newsletter tab added to nav (Newsletters 0)
- Flask route /newsletters added (line ~964)
- Bug: newsletter code leaked out of downloadBriefing() template string causing JS SyntaxError → page stuck on "Checking server…"
- Fix: removed duplicate style/script blocks, closed template string, added missing </script> tag
- Bloomberg Auto-clip button added (mirrors FT)
- Settings page added (settings.html) for cookie management
- 24h activity bar added

### 20 March 2026
- HTTP server launchd plist added (com.alexdakers.meridian.http.plist) — now auto-starts on login
- Bloomberg cookies were missing from cookies.json — refreshed via settings.html
- run_bookmarks_sync() updated to call fetch_bloomberg_api() for Bloomberg instead of fetch_bookmarks_for_pub()
- Bloomberg API response format confirmed: HAL format, data._embedded.items[].metadata.{url, headline.text}
- fetch_bloomberg_api() and BloombergScraper in-browser API both return 0 — Bloomberg pagination still broken
- FT "sync found 0 articles" warning confirmed as false alarm — FT syncing correctly via Playwright
- credentials.json deleted earlier (was Google OAuth file) — broke AI analysis
- New Anthropic API key created and stored in credentials.json
- AI analysis confirmed working with 202 articles
- Fixed JS guard: norm() function now handles undefined tags (s||'').toLowerCase()
- Fixed JS guard: data.content response now handles empty API responses
- Status filter bug fixed: "Title only" filter now correctly shows both title_only and fetched articles
- Economist articles clipped to full text (14 articles)
- Extension popup.js fix: strips "Your browser does not support the" audio fallback text from clips
- Gmail OAuth access revoked (myaccount.google.com/permissions) — Meridian app removed
- token.json and credentials.json deleted locally
- meridian_smtp.py created (local SMTP server on port 2525) — tested and working
- com.alexdakers.meridian.smtp.plist created and loaded
- Newsletter approach decided: RSS feeds for Substack (no Gmail access needed)
- POP3 approach ruled out — App Passwords not available on this Google account

## Build History

### 25 March 2026
- FA pub_date: fixed selector to `span.topper__date` (was looking for `time[datetime]` which doesn't exist on FA), backfilled all 31 articles
- Economist pub_date: extracted from URL pattern `/YYYY/MM/DD/`, backfilled all 86 articles — no scraping needed
- Economist auto-clip: `fetch_economist_article_text` now called during sync for both new articles and any existing `fetched` articles — full parity with FT/FA
- Removed cookie-based bookmarks sync entirely: `run_bookmarks_sync()`, `bookmarks_sync_status`, `/api/bookmarks/sync` endpoint, background thread in server.py, and `syncBookmarks()` in meridian.html — was generating 403 noise and redundant with Playwright scrapers
- DB: ~287 articles, all sources now have correct pub_dates
- FT/Economist/FA pub_date backfill complete — 0 malformed dates remaining
- FT: 1 title_only article missing date (no URL) — acceptable
- FT headless=False required for article scraping (headless=True gets Access Error)
- Removed 4 duplicate FT articles with wrong dates
- FA no-URL article (fa_1773665346633) manually set to 2026-03-01T00:00:00Z
- Newsletter pipeline built (25 Mar 2026):
  - iCloud alias: meridian.newsletters@icloud.com
  - Gmail auto-forwards from noreply@news.bloomberg.com and bloomberg@mail.bloomberg.com
  - newsletter_sync.py polls iCloud IMAP (alex.dakers@icloud.com, app-specific password)
  - Stores in newsletters DB table: source, subject, body_html, body_text, received_at
  - Flask route: /api/newsletters/sync (POST)
  - 🔄 Newsletters button added to Meridian header
  - Scheduler runs newsletter sync every 6h alongside article sync
  - iCloud IMAP: host=imap.mail.me.com, port=993, auth with primary address not alias
  - iCloud requires BODY[] not RFC822 for fetch
  - App-specific password stored in newsletter_sync.py
- Next: wire up newsletters tab UI to display stored newsletters

### 25 March 2026 (continued)
- Newsletter tab UI complete: click to expand shows full HTML email in iframe with charts/images
- Newsletter rendering: preview (200 chars plain text) → click → full HTML iframe (800px)
- Bloomberg removed from all code (server.py, meridian.html, settings.html, extension/popup.js) — articles kept in DB
- Removed: BloombergScraper, fetch_bloomberg_article_text, fetch_bloomberg_api, BBG sync button, Bloomberg filter, Bloomberg activity bar, BBG settings section
- WARNING: Bloomberg removal script accidentally deleted all Flask routes from server.py — had to reconstruct from session context. Set up git to avoid this in future.
- Newsletter pipeline complete:
  - iCloud alias: meridian.newsletters@icloud.com (app password: iwjx-qkgo-ntat-yunw)
  - Gmail auto-forwards from noreply@news.bloomberg.com and bloomberg@mail.bloomberg.com
  - newsletter_sync.py polls iCloud IMAP every 6h, stores in newsletters table
  - Flask route: /api/newsletters/sync (POST)
  - 🔄 Newsletters button in header triggers manual sync
  - renderNewsletters() fetches from /newsletters API, renders HTML in iframe on click
- Next session: set up git repo for server.py backup

## Next Session
- Add standalone "Ask AI" button for general freeform queries against the full article DB (not tied to the AI Analysis panel presets)
