with open('/Users/alexdakers/meridian-server/NOTES.md', 'r') as f:
    content = f.read()

old = """**Session 58 agenda:**
1. FT enrichment backlog: ~30 pending title_only — trigger enrichment
2. Feed filter Stats/Bloomberg tab-switch stacking — still needs CSS fix
3. FA scraper: FA cookie renewal (expires 2026-05-23)
4. Economist bookmarks zero-days: investigate whether CDP port binding issue persists"""

new = """**Session 58 agenda:**
1. **FT enrichment — renew ft_profile session**: FT enrichment broken because ft_profile Playwright session expired. Need to open Chrome with ft_profile and log in manually to renew cookies. Zero articles being enriched (0/30-60 per run).
2. **Chrome MCP enrichment**: Investigate using the logged-in Chrome session via Claude Chrome MCP to click through FT/Economist articles and enrich them directly — avoids Playwright session management entirely.
3. **Bloomberg newsletters swim lane**: Add a swim lane in the stats panel showing Bloomberg newsletter articles (already in Newsletters tab). These are Bloomberg email digests already being scraped.
4. **Bloomberg newsletter link extraction + AI scoring**: Parse Bloomberg newsletter bodies for embedded article links, fetch and score them via Sonnet, add qualifying articles to Feed/Suggested. Similar to web agent but sourced from newsletters we already have.
5. Feed filter Stats/Bloomberg tab-switch stacking — CSS fix still pending
6. FA scraper: FA cookie renewal (expires 2026-05-23)
7. Economist bookmarks CDP port binding — monitor for recurrence"""

content = content.replace(old, new, 1)
with open('/Users/alexdakers/meridian-server/NOTES.md', 'w') as f:
    f.write(content)
print("NOTES.md updated")
