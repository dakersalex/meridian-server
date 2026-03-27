# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Meridian is a personal news aggregator that scrapes articles from Financial Times, The Economist, and Foreign Affairs using Playwright browser automation. It stores them in SQLite, serves them via a Flask REST API, and enriches them with Claude AI (summaries, tags, topics, scoring). The frontend is a single-file HTML5 SPA (`meridian.html`).

**Live:** https://meridianreader.com — Hetzner VPS in Helsinki, Flask behind nginx with Let's Encrypt SSL.

## Running Locally

```bash
python setup.py                           # First time: install deps, create credentials.json
python server.py                          # Flask at http://localhost:4242
SYNC_INTERVAL_HOURS=12 python server.py   # Custom sync interval (default: 6h)
python sync_now.py                        # Manual sync all sources
python sync_now.py ft                     # Sync single source (ft, economist, fa)
```

No automated test suite exists. Testing is manual.

## VPS Deployment

```bash
# On VPS (ssh root@meridianreader.com):
cd /opt/meridian-server && git pull && systemctl restart meridian
journalctl -u meridian -f   # View logs
```

## Architecture

### server.py (~1450 lines) — the entire backend

Everything lives in one file. Key sections by line range:

- **Constants & DB helpers (26-119):** `DB_PATH`, `init_db()`, `upsert_article()`, `make_id()` (SHA1 of source:url for dedup)
- **AI enrichment (120-181):** `enrich_article_with_ai()` — Claude Haiku generates summary, fullSummary, keyPoints, tags, topic, pub_date
- **Content extraction (183-266):** `fetch_ft_article_text()`, `fetch_economist_article_text()` etc. — BeautifulSoup with multiple fallback CSS selectors
- **Scraper classes (268-507):** `FTScraper`, `EconomistScraper`, `ForeignAffairsScraper` — Playwright with persistent login profiles (`ft_profile/`, `economist_profile/`, `fa_profile/`)
- **SCRAPERS registry (509):** `{"ft": FTScraper, "economist": EconomistScraper, "fa": ForeignAffairsScraper}`
- **Threading & scheduling (511-533):** Background threads for non-blocking syncs, quiet hours 1-6am UTC
- **Suggested articles pipeline (1064-1323):** Scrapes most-read + Claude agentic web search (tool_use loop, up to 6 roundtrips, 30s rate limit) → Claude scoring 0-10 → dedup
- **Flask routes (rest of file):** REST API at `/api/*`

### meridian.html (~3000+ lines) — the entire frontend

Single-page app with tabs: Feed, Suggested, Interviews, Newsletters, Settings. Playfair Display + IBM Plex Sans. Dark mode via prefers-color-scheme. Responsive.

### extension/ — Chrome extension (Manifest V3)

Saves articles from any page to Meridian. Auto-harvests cookies from publication sites. `SERVER` constant in `background.js` points to server URL.

### Database (SQLite)

5 tables: `articles` (main feed), `sync_log` (audit), `suggested_articles` (inbox model: new→reviewed→saved/dismissed), `interviews` (video/podcast), `newsletters` (email archive). Article IDs are SHA1 hashes of `source:url`.

## Key Patterns

- **Idempotent scrapers:** SHA1 IDs prevent duplicates; scrapers exit early when hitting existing articles
- **Persistent Playwright profiles:** Browser dirs (`ft_profile/` etc.) maintain login state across runs
- **Async threading:** Syncs run in background threads; API remains responsive
- **Inbox model for suggestions:** Status-based workflow (new → reviewed → saved/dismissed) with Claude relevance scoring
- **Fallback CSS selectors:** Multiple selectors per source for robust content extraction when sites change layouts

## Credentials & Security

`credentials.json` (git-ignored, chmod 600) contains publication logins and `anthropic_api_key`. The repo is public — never commit secrets. Other git-ignored files: `cookies.json`, `meridian.db`, `newsletter_sync.py`, browser profiles, `venv/`.

## Adding a New Source

1. Create a scraper class in `server.py` following the `FTScraper`/`EconomistScraper` pattern
2. Add a `fetch_<source>_article_text(page, url)` content extraction function
3. Register in the `SCRAPERS` dict
4. Optionally add to the suggested articles pipeline's scraping step
