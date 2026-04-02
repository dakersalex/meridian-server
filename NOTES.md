# Meridian — Technical Notes
Last updated: 2 April 2026 (Session 35 — permanent/manual themes, key_facts fix, theme consolidation)

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
One command from Mac Terminal:
  cd ~/meridian-server && ./deploy.sh "description"

(deploy.sh: git add -A, commit, push, SSH pull on VPS, systemctl restart meridian)

## Database (2 April 2026)
Total: ~531 articles (VPS)
- Financial Times: ~155 / The Economist: ~260 / Foreign Affairs: ~52 / Bloomberg: ~38 / Other: ~26

---

## Autonomous Mode (Claude in Chrome + shell endpoint)

### CRITICAL: Claude must ALWAYS run commands autonomously
Claude has full access to run all terminal commands, patches, and deployments via:
- **Filesystem MCP** — write patch scripts to ~/meridian-server/
- **Shell bridge** — execute via window.shell() in Tab A (localhost)
- **deploy.sh** — commit, push and deploy to VPS in one command

**Claude must NEVER ask Alex to run commands in Terminal.** This includes:
- Running patch scripts (always: filesystem:write_file → window.shell('python3 ~/meridian-server/tmp_*.py'))
- Syntax checks (always: window.shell('python3 -m py_compile ~/meridian-server/server.py'))
- Deploying (always: window.shell('cd ~/meridian-server && ./deploy.sh "message"'))
- SSH commands to VPS (always: write script → window.shell with subprocess/ssh)
- Checking logs (always: fetch via shell bridge, write to tmp file, read via Filesystem MCP)

Alex is not present during execution. Complete all tasks end-to-end autonomously.

### Shell bridge
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

### NEVER restart Flask via shell endpoint — it kills itself mid-request

### Key patterns
- Write patch scripts via filesystem:write_file → execute via window.shell()
- VPS Python: write script → deploy.sh (never inline -c strings with nested quotes)
- Shell endpoint filters keywords: base64-encode output or write to /tmp/ if needed
- Line-number based patches are DANGEROUS — always use str.replace(OLD, NEW) with exact text
- Always python3 -m py_compile server.py before deploying
- After deploying, verify via live site tab (Tab B)

### Dangerous operations checklist
Before any DELETE/UPDATE: SELECT preview first, state what will be affected, then execute.

---

## Key Themes (KT) System

### Current state (after Session 35)
- **8 themes** (changed from 10) — sorted by article count descending
- Seed prompt enforces consolidation: no geographic theatre splits, no tech race splits
- key_facts: populated via Haiku Call 3 (max_tokens fixed to 2500, timeout 45s)
- 531 articles tagged on VPS

### Theme grid design (Session 35)
- **8 AI-generated themes** sorted by matched article count (most articles top-left)
- **2 manual slots** (silver dashed border) — always shown at end of grid
  - Click to open modal: name + keywords + emoji
  - Stored in localStorage as `meridian_manual_themes`
  - Auto-marked permanent on creation
- **★ Permanent themes** (gold border + "PERMANENT" badge)
  - Click ☆ star button on any AI theme card to make it permanent
  - Stored in localStorage as `meridian_permanent_themes`
  - Survive Reset Themes — listed in confirm dialog before reset
  - Deselect ★ before reset to allow that theme to be freely regenerated
- **Reset Themes confirm dialog** lists all permanent themes by name

### kt/seed pipeline (3-call architecture)
- **Call 1** — Sonnet: 165 representative titles → 8 themes (name, emoji, keywords, overview, subtopics)
  max_tokens=3000, timeout=60s
- **Call 2** — Haiku: all articles in batches of 50 → article→theme assignments
- **Call 3** — Haiku: one theme at a time → key_facts + subtopic_details
  max_tokens=2500, timeout=45s, non-fatal if individual theme fails

### Seeding prompt rules (Call 1)
- Requests exactly 8 themes
- Consolidation rules: never split same geographic theatre, never split same tech race
- Bans generic keywords: war, military, conflict, economy, geopolitics, policy, crisis, markets

### getThemeArticles() matching logic (meridian.html)
Three-layer filter, all word-boundary regex (\b):
1. Anchor gate: keywords[0] must appear in title or summary
2. 2-hit requirement: ≥2 keywords in title+summary combined
3. Single-hit fallback: anchor + corroborating tag/topic

---

## Intelligence Brief Pipeline (✅ WORKING)

### Overview
- brief_pdf.py — standalone module, ReportLab + Pillow, generates A4 PDF
- Single Sonnet call: text generated once, used for both modal display and PDF build
- Full brief includes Economist charts; short brief is text only

### Article context (_build_article_context in brief_pdf.py)
- Temporal bucketing: 4 equal time buckets × 15 articles = up to 60 (full brief)
- Within each bucket: full_text articles first, then by summary length
- Per-source cap: 5 per bucket for source diversity

### Chart selection rules
- No charts in: Executive Summary, Overview, Cross-cutting Themes, Strategic Implications,
  Watch List, Key Developments, Source Notes
- Cross-brief similarity dedup: >50% description token overlap → rejected
- Solo charts (only 1 qualifies) → 0 shown (never unpaired)
- Budget: up to 2 per section, global cap 14 charts per brief

---

## Flask Routes — Brief Pipeline
- POST /api/kt/brief             — text brief (async), returns {ok, job_id}
- GET  /api/kt/brief/status/<id> — poll {status, brief, error}
- POST /api/kt/brief/pdf         — PDF job, accepts optional {text} pregenerated_text
- GET  /api/kt/brief/pdf/status/<id>   — poll
- GET  /api/kt/brief/pdf/download/<id> — serve PDF
- POST /api/kt/brief/context-debug     — article bucket debug
- POST /api/kt/seed              — full reseed
- GET  /api/kt/seed/status/<id>  — poll seed job

---

## Economist Chart & Map Capture (Session 26 ✅)

### DB state (2 April 2026)
- Mac: 156 images, 86 articles with images
- VPS: synced via push-images on each wake_and_sync.sh run

### Image sync to VPS
- POST /api/push-images — receives images from Mac, upserts on mac_id

---

## Service Worker
- sw.js cache version: meridian-v5
- nginx: no-cache for meridian.html and sw.js

## Schedule (Geneva/CEST)
- 05:40 / 11:40 — Mac syncs FT + Economist + FA via Playwright
- 05:50 / 11:50 — VPS scores, agent auto-saves 8+ to Feed

---

## Next Steps (priority order)
1. **Trigger Reset Themes** on live site — current themes have key_facts=0 (fixed in this session,
   needs one more reset with new max_tokens=2500 to populate)
2. **AI theme split persists** — "US-China Tech and Trade War" + "Western AI Industry and Investment"
   still appearing as two themes despite consolidation rule. May need to name them explicitly
   in the prompt as a must-merge example.
3. **Sort theme articles by relevance** — article list in theme detail panel shows most recent first;
   better UX: sort by keyword hit count + summary length so most substantive articles surface first.
4. **Sub-topics filtering** — chips in theme panel do nothing; decide: implement filtering or remove
   and use subtopics only as brief section headings.
5. **Focused Intelligence Briefing** — free-text input for ad-hoc topic briefs not tied to 8 themes.
6. **Clean up tmp_ files** — many tmp_*.py, tmp_*.txt accumulated across sessions.
   Run via shell bridge: cd ~/meridian-server && git rm --ignore-unmatch tmp_*.py tmp_*.txt tmp_*.png && git commit -m "chore: remove tmp files"
7. **Foreign Affairs paywall** — FA articles still truncating at ~1,400 chars.
   Investigate fa_profile/ cookie freshness, try re-login via Playwright.

---

## Build History

### 2 April 2026 (Session 35 — theme consolidation, permanent/manual themes)

**Theme count: 10 → 8**
- Seed prompt updated to request exactly 8 themes
- Consolidation rules added: no geographic theatre splits, no tech race splits
- Consumer/luxury only gets theme if article volume justifies it
- Tighter ban on generic keywords

**key_facts fix**
- Root cause: max_tokens=1500 was truncating Haiku JSON mid-response
- Fix: max_tokens 1500 → 2500, timeout 30 → 45s for Call 3
- Hardcoded "/10" references fixed to use len(themes) dynamically
- Duplicate call_anthropic bug (resp1 called twice) also fixed

**Permanent + Manual theme grid**
- Themes sorted by matched article count descending (most articles top-left)
- ★ star button on each AI theme card — click to mark permanent (gold border)
- Permanent themes stored in localStorage as `meridian_permanent_themes`
- 2 manual slots always visible at end of grid (silver dashed border)
- Manual theme modal: name + keywords + emoji
- Manual themes stored in localStorage as `meridian_manual_themes`
- Reset Themes confirm dialog lists permanent themes by name
- Previous "pinned topics" row replaced by this card-level system

**Commits this session**
- 14383d41  feat: seed 8 consolidated themes with anti-overlap rules; fix duplicate resp1
- ad080d49  feat: pinned topics row on Key Themes; fix key_facts max_tokens 1500->2500
- [current] feat: permanent/manual theme grid, sorted by article count, gold/silver cards

### 1 April 2026 (Session 34 — article filtering & brief quality)
- getThemeArticles() tighter keyword matching (word-boundary regex, anchor gate, 2-hit requirement)
- kt/seed 3-call architecture with Haiku per-theme key_facts
- Seeding prompt requests specific discriminating keywords, bans generic terms
- VPS SyntaxError recovery (duplicate theme_prompt fragment)

### 1 April 2026 (Sessions 29-31 — brief PDF pipeline)
- Single Sonnet call architecture, unified prompt, richer article context
- Chart image processing: top/bottom crop, whitening, figure captions
- PDF layout: maps full-width, charts paired half-width

### Earlier sessions (26-28)
- Economist chart capture, insight enrichment, article_images sync Mac→VPS
- KT themes initial implementation

---

## GitHub Visibility
- Repo: PUBLIC — github.com/dakersalex/meridian-server
- Excluded: credentials.json, cookies.json, meridian.db, newsletter_sync.py, venv/

## Session Starter Prompt
---
You are helping me build Meridian, my personal news aggregator. Please read my technical notes from the Filesystem MCP at /Users/alexdakers/meridian-server/NOTES.md and review them. Then run the session start health check.
---

Note for Claude: Read NOTES.md via Filesystem MCP (NOT GitHub URL — blocked). Run all commands autonomously via shell bridge — NEVER ask Alex to run Terminal commands. Check Flask via shell endpoint before proceeding. Never restart Flask via the shell endpoint.
