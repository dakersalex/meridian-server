# Meridian Scraper Server

A local Python server that logs into your FT, Economist, and Bloomberg accounts,
fetches your saved articles, and serves them to the Meridian app over a local API.

---

## Requirements

- Python 3.10 or later
- macOS, Linux, or Windows with WSL

---

## First-time setup (takes ~3 minutes)

```bash
cd meridian-server
python setup.py
```

This will:
1. Install Flask, Playwright, BeautifulSoup and other dependencies
2. Download a headless Chromium browser
3. Ask for your FT / Economist / Bloomberg email & password
4. Save credentials locally in `credentials.json` (chmod 600 — only your user can read it)

---

## Running the server

```bash
python server.py
```

The server starts at **http://localhost:4242** and keeps running in the background.
It will automatically sync all sources every 6 hours.

To change the sync interval:
```bash
SYNC_INTERVAL_HOURS=12 python server.py
```

### Keep it running persistently (macOS)

Create a launchd plist so the server starts on login:

```bash
# Edit the path below to match where you put meridian-server
cat > ~/Library/LaunchAgents/com.meridian.server.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.meridian.server</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/YOUR/PATH/TO/meridian-server/server.py</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardErrorPath</key>
  <string>/tmp/meridian.err</string>
</dict>
</plist>
EOF

launchctl load ~/Library/LaunchAgents/com.meridian.server.plist
```

---

## Manual one-off sync

```bash
python sync_now.py            # all sources
python sync_now.py ft         # FT only
python sync_now.py economist  # Economist only
python sync_now.py bloomberg  # Bloomberg only
```

---

## Bloomberg — first-run note

Bloomberg has aggressive bot detection. On the **first run**, the browser will
open in a visible window and ask you to log in manually. After that, your session
is saved in `bloomberg_profile/` and subsequent syncs run headlessly.

---

## API endpoints (for reference)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Server health check |
| GET | `/api/articles` | All articles (add `?source=ft` to filter) |
| POST | `/api/sync` | Trigger sync (`{"source":"all"}` or specific) |
| GET | `/api/sync/status` | Current sync status per source |
| POST | `/api/credentials` | Update credentials |
| DELETE | `/api/articles/:id` | Delete an article |
| PATCH | `/api/article/:id/topic` | Update topic/tags |

---

## File layout

```
meridian-server/
├── server.py          ← main server (run this)
├── setup.py           ← first-time setup
├── sync_now.py        ← manual sync trigger
├── credentials.json   ← your login credentials (chmod 600, git-ignored)
├── meridian.db        ← SQLite database of articles
├── meridian.log       ← server logs
└── bloomberg_profile/ ← Playwright browser profile (Bloomberg session)
```

---

## Security notes

- `credentials.json` is set to `chmod 600` — only readable by you
- The server only listens on `127.0.0.1` (localhost) — not accessible from the network
- No credentials or article content is ever sent to any third party
- Add `credentials.json` and `bloomberg_profile/` to your `.gitignore` if you use git
