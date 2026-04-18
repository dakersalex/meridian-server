import re

with open('/Users/alexdakers/meridian-server/NOTES.md', 'r') as f:
    content = f.read()

content = content.replace(
    "Last updated: 17 April 2026 (Session 57 — Economist weekly AI pick rewrite, Suggested UI polish, CDP monitoring)",
    "Last updated: 18 April 2026 (Session 58 — reverted MCP enrichment attempt, lean feed endpoint, FT pub_date fix)"
)

old_agenda = """**Session 58 agenda:**
1. **FT enrichment — renew ft_profile session**: FT enrichment broken because ft_profile Playwright session expired. Need to open Chrome with ft_profile and log in manually to renew cookies. Zero articles being enriched (0/30-60 per run).
2. **Chrome MCP enrichment**: Investigate using the logged-in Chrome session via Claude Chrome MCP to click through FT/Economist articles and enrich them directly — avoids Playwright session management entirely.
3. **Bloomberg newsletters swim lane**: Add a swim lane in the stats panel showing Bloomberg newsletter articles (already in Newsletters tab). These are Bloomberg email digests already being scraped.
4. **Bloomberg newsletter link extraction + AI scoring**: Parse Bloomberg newsletter bodies for embedded article links, fetch and score them via Sonnet, add qualifying articles to Feed/Suggested. Similar to web agent but sourced from newsletters we already have.
5. Feed filter Stats/Bloomberg tab-switch stacking — CSS fix still pending
6. FA scraper: FA cookie renewal (expires 2026-05-23)
7. Economist bookmarks CDP port binding — monitor for recurrence"""

new_agenda = """**Session 58 outcomes:**
- MCP enrichment attempted but Chrome MCP blocks paywalled sites (economist.com, ft.com) — approach abandoned
- All MCP enrichment code removed (enrich-via-browser endpoints, button, JS)
- Reverted server.py + meridian.html to pre-MCP state (commit 4f867800)
- FT pub_date fix: fallback to today's date when publishedDate absent in feed
- Lean /api/articles/feed endpoint added: returns title/meta only (260KB vs 3.6MB) — fixes page load speed
- Economist scraper: max_clicks reduced 60→10, cutoff_date early stop added to prevent runaway bookmark scraping
- eco_weekly_sub.py: CDP port fix (9223, 127.0.0.1, port-poll) — was ECONNREFUSED on macOS
- vps_push.py: suggested push fixed (DB_PATH→DB, VPS_BASE→hardcoded, cutoff_48h variable)

**Key lessons from Session 58:**
- Chrome MCP cannot navigate to paywalled sites — do not attempt MCP-based article enrichment
- launchd throttles Flask after repeated restarts — use /api/dev/restart sparingly, batch deploys
- The /api/dev/restart endpoint is preferred over kill -9 for Flask restarts
- FT enrichment (Playwright) is blocked by FT bot detection — not a session expiry issue

**Session 59 agenda:**
1. **Bloomberg newsletters swim lane**: Add Bloomberg to stats panel swim lanes (data already in Newsletters tab)
2. **Bloomberg newsletter link extraction + AI scoring**: Parse newsletter bodies for article links, score with Haiku, route to Feed/Suggested
3. **Economist login**: eco_chrome_profile session expired — needs fresh login via eco_login_setup.py before next scheduled scrape
4. **FT enrichment**: Accept title_only for FT AI picks; FT Playwright enrichment blocked by bot detection
5. FA cookie renewal check (expires 2026-05-23)"""

content = content.replace(old_agenda, new_agenda, 1)

with open('/Users/alexdakers/meridian-server/NOTES.md', 'w') as f:
    f.write(content)
print("NOTES.md updated")
