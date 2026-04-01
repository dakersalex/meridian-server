# Meridian — Technical Notes
Last updated: 1 April 2026 (Session 34 — article filtering & brief quality)

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

## Database (1 April 2026)
Total: ~523 articles (Mac), ~520 articles (VPS)
- Financial Times: 153 / The Economist: 257 / Foreign Affairs: 46 / Bloomberg: 38 / Other: ~26

---

## Key Themes (KT) System

### Current state (after Session 34 re-seed)
- 10 themes, 521 tagged articles on VPS
- Themes re-seeded with improved keyword prompt (specific discriminating terms)
- key_facts: STILL BLANK — see "Pending: one more Reset Themes" below

### Theme names (latest seed)
1. Global Financial Markets Volatility
2. US-Iran Military Conflict
3. US Domestic Power and Governance
4. European Security and Politics
5. AI Development and Disruption
6. Gulf Energy Markets Shock
7. China Strategy and Technology
8. Middle East Regional Dynamics
9. Trump Trade War and Tariffs
10. Ukraine and New Warfare

### kt/seed pipeline (3-call architecture)
- **Call 1** — Sonnet, 165 representative article titles → 10 themes (name, emoji, keywords,
  overview, subtopics). max_tokens=3000, timeout=60s.
- **Call 2** — Haiku, all articles in batches of 50 → article→theme assignments.
- **Call 3** — Haiku, one theme at a time → key_facts (10 facts) + subtopic_details.
  timeout=30s per theme, non-fatal if individual theme fails.

### PENDING: one more Reset Themes needed
Key Facts are still blank because the last re-seed ran against the old server code
(before the Haiku per-theme fix was deployed). The fix is live now. Trigger
Reset Themes one more time from the live site to populate key_facts.

### getThemeArticles() matching logic (meridian.html)
Three-layer filter, all word-boundary regex (\b):
1. **Anchor gate** (hard block): `keywords[0]` must appear in title or summary.
   Articles with no summary → excluded entirely (nothing to contribute to brief).
2. **2-hit requirement**: ≥2 keywords must appear in title+summary combined.
3. **Single-hit fallback**: anchor matches + corroborating tag/topic qualifies
   (for well-tagged articles with brief summaries).

Anchor keywords per theme (keywords[0]):
- Iran War → "Iran" | Financial Markets → "markets" | Trump FP → "Trump"
- AI → "AI" | Energy → "oil" | China → "China" | Europe → "Europe"
- Trade War → "tariffs" | Private Credit → "private credit" | Crypto → "crypto"

### Seeding prompt (server.py kt_generate + kt/seed Call 1)
Explicitly requests specific discriminating terms: named entities, proper nouns,
places, organisations. Bans generic terms like "war", "military", "economy",
"geopolitics". Example given for Iran theme: Iran, IRGC, Hormuz, Revolutionary Guard,
Khamenei, Strait, Tehran, Houthi, sanctions, ceasefire, airstrike, Persian Gulf.

---

## Intelligence Brief Pipeline (✅ WORKING)

### Overview
- brief_pdf.py — standalone module, ReportLab + Pillow, generates A4 PDF
- Single Sonnet call: text generated once, used for both modal display and PDF build
- Full brief includes Economist charts (subtopic sections only); short brief is text only

### User flow
1. Click "Short Brief" or "Full Intelligence Brief" on any theme
2. Modal opens with progress spinner — rotating step labels + elapsed seconds
3. ~60-90s later text brief renders in modal (Executive Summary in amber panel)
4. "⇓ Open as PDF" button top-right opens PDF in new tab
5. PDF built from same text (no second Sonnet call), charts embedded, text justified

### Article context (_build_article_context in brief_pdf.py)
- Temporal bucketing: 4 equal time buckets × 15 articles = up to 60 (full brief)
- Within each bucket: full_text articles first, then by summary length
- Per-source cap: 5 per bucket for source diversity
- Date parsing: handles ISO YYYY-MM-DD, "26 March 2026", "March 2026" etc.
- Falls back to saved_at ms ÷ 86400000 if no pub_date

### Context-debug endpoint
- POST /api/kt/brief/context-debug — shows full bucket breakdown with dates, scores, sources
- Useful for verifying article selection quality before generating briefs

---

## Chart Image Processing (_crop_economist_chart in brief_pdf.py)

### Top crop, bottom crop, whitening — see Session 31 notes (unchanged)

### Chart selection rules
- No charts in: Executive Summary, Overview, Cross-cutting Themes, Strategic Implications,
  Watch List, Key Developments, Source Notes
- Cross-brief similarity dedup: >50% description token overlap → rejected
- Solo charts (only 1 qualifies for a section) → 0 charts shown (never unpaired)
- Budget: up to 2 per section, global cap 14 charts per brief

---

## Flask Routes — Brief Pipeline
- POST /api/kt/brief             — text brief (async), returns {ok, job_id}
- GET  /api/kt/brief/status/<id> — poll {status, brief, error}
- POST /api/kt/brief/pdf         — PDF job (async), accepts optional {text} pregenerated_text
- GET  /api/kt/brief/pdf/status/<id>   — poll {status, ready, size, error}
- GET  /api/kt/brief/pdf/download/<id> — serve completed PDF
- POST /api/kt/brief/context-debug     — article bucket debug (dev tool)
- POST /api/kt/seed              — full reseed (wipes + rebuilds)
- GET  /api/kt/seed/status/<id>  — poll seed job

---

## Economist Chart & Map Capture (Session 26 ✅)

### DB state (1 April 2026)
- Mac: 153 images, 153 with insight
- VPS: 153 images, mac_id dedup prevents duplicates

### Image sync to VPS
- POST /api/push-images — receives images from Mac, upserts on mac_id
- wake_and_sync.sh pushes images on every sync

---

## Autonomous Mode (Claude in Chrome + shell endpoint)

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
- Line-number based patches are DANGEROUS — they insert without removing old block.
  Always use string replacement (src.replace(OLD, NEW)) with exact text matching.

### Dangerous operations checklist
Before any DELETE/UPDATE: SELECT preview first, state what will be affected, then execute.

---

## Service Worker
- sw.js cache version: meridian-v5
- nginx: no-cache for meridian.html and sw.js

## Schedule (Geneva/CEST)
- 05:40 / 11:40 — Mac syncs FT + Economist + FA via Playwright
- 05:50 / 11:50 — VPS scores, agent auto-saves 8+ to Feed

---

## Next Steps (priority order)
1. **Reset Themes one more time** — key_facts are blank, Haiku-per-theme fix is now
   deployed. Trigger from live site: Key Themes → Reset Themes.
2. **Clean up tmp_ files** — many tmp_*.py, tmp_*.png accumulated across sessions.
   Run: git rm tmp_*.py tmp_*.png *.png crop_*.png orig_*.png && git commit -m 'chore: remove tmp files'
3. **Foreign Affairs paywall** — FA articles still truncating at ~1,400 chars.
   Investigate fa_profile/ cookie freshness, try re-login via Playwright.
4. **Chart-to-brief integration review** — chart selection scoring works well; consider
   whether _MIN_SCORE threshold is right for non-Iran-war themes.
5. **KT keywords UI** — no in-app way to view/edit theme keywords; consider adding
   to theme detail panel.

---

## Build History

### 1 April 2026 (Session 34 — article filtering & brief quality)

**getThemeArticles() — tighter keyword matching**
- Word-boundary regex (\bkeyword\b) prevents "war" matching "software"
- Anchor gate: keywords[0] must appear in title or summary (hard block)
- 2-hit requirement: ≥2 keywords in title+summary for articles with summaries
- Title-only articles (no summary) excluded entirely — no content for brief context
- Single-hit + tag fallback for well-tagged articles with brief summaries

**Seeding prompt improvements**
- Now requests 12-16 specific discriminating keywords (named entities, proper nouns)
- Explicitly bans generic terms like "war", "military", "economy", "geopolitics"
- Re-seeded: 10 new themes with specific anchors (Iran, Trump, China, AI, oil, etc.)

**kt/seed 3-call architecture (timeout fix)**
- Call 1 reverted to themes-only (fast, 60s): name/emoji/keywords/overview/subtopics
- Call 2: Haiku batches article→theme assignment (unchanged)
- Call 3: Haiku per-theme key_facts generation (new) — one theme at a time, 30s each
  Fixes the "read operation timed out" error from trying to do all 10 in one Sonnet call

**key_facts pipeline**
- Root cause: kt/seed was a 2-call system; key_facts were supposed to be generated
  "later" but that second pass was never implemented, leaving key_facts = []
- Fix: Call 3 generates key_facts + subtopic_details per theme using Haiku
- key_facts still blank after latest seed because it ran before the fix deployed.
  Pending one more Reset Themes.

**VPS outage (server offline)**
- Caused by a line-number patch that inserted new theme_prompt block without removing
  old fragment → duplicate unclosed paren → SyntaxError on startup
- Fixed by tmp_fix_dupe.py which detected both occurrences and removed the corrupt first one
- Learning: NEVER use line-number insertion patches. Always use str.replace(OLD, NEW).

**Commits this session**
- 7692abd  fix: tighter keyword matching in getThemeArticles
- eddd4cd7 fix: specific discriminating keywords in seed prompt, 2+ content hits
- cc5a16e2 feat: anchor keyword gate — keywords[0] must appear in title/summary
- 302296bb fix: exclude title-only articles from getThemeArticles
- 76ad609  fix: kt/seed includes key_facts + subtopic_details (caused timeout)
- [fix]    fix: remove duplicate theme_prompt fragment causing SyntaxError on VPS
- [fix]    fix: split kt/seed Call 3 — Haiku per theme, 30s timeout, non-fatal
- [fix]    fix: key_facts via Haiku one theme at a time — no timeout

### 1 April 2026 (Session 33 — temporal bucketing & seed quality)
- _build_article_context: 4 time buckets × 15 articles, full_text first, source cap
- Date parsing cascade: ISO, "26 March 2026", "March 2026", etc.
- Context-debug endpoint added
- Seed prompt updated to request specific discriminating keywords

### 1 April 2026 (Sessions 29-31 — brief PDF pipeline)
- Single Sonnet call architecture, unified prompt, richer article context
- Chart image processing: top/bottom crop, whitening, figure captions
- PDF layout: maps full-width, charts paired half-width
- pdfJobId null race condition fixed (window._pdfJobId)
- sw.js fixed, cache v5, nginx no-cache headers

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

Note for Claude: Read NOTES.md via Filesystem MCP (NOT GitHub URL — blocked). Check Flask via shell endpoint before proceeding. Never restart Flask via the shell endpoint.
