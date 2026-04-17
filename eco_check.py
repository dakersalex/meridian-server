import re

with open('/Users/alexdakers/meridian-server/NOTES.md', 'r') as f:
    content = f.read()

# Update header
content = content.replace(
    "Last updated: 16 April 2026 (Session 56 — AI pick overhaul, FA scoring fixes, threshold changes)",
    "Last updated: 17 April 2026 (Session 57 — Economist weekly AI pick rewrite, Suggested UI polish, CDP monitoring)"
)

# Add Session 57 entry before Session 56
old_s56 = "### 16 April 2026 (Session 56)"
new_s57 = """### 17 April 2026 (Session 57)

**Suggested tab — UI overhaul complete**
- Feed filter bar (feed-header-outer) hidden on Suggested/Newsletters/Interviews tabs
- Suggested filter bar rendered as child div inside feed-header-outer — sticky, same bg/border
- Stats and Clip Bloomberg buttons hidden on Suggested tab, restored on Feed (display:flex / display:contents)
- Sort toggle (★ Score / 📅 Date) added and working end-to-end
- Date format: all suggested dates normalised to YYYY-MM-DD on Mac + VPS; formatPubDate() used for display
- formatPubDate() fallback: saved_at || added_at (suggested has added_at not saved_at)
- Loading suggestions... ghost text fixed (cleared after header renders into fho)
- Feed tab restore fixed: Stats/Bloomberg restore as flex correctly on switch back
- Save to Feed button: accent outline style

**Suggested sync**
- vps_push.py: suggested push fixed — DB_PATH→DB, VPS_BASE→hardcoded, cutoff_48h variable

**Economist weekly AI pick — complete rewrite**
- Source: /weeklyedition/archive to find 2 most recent edition URLs dynamically
- eco_weekly_sub.py: standalone subprocess, port 9223 (not 9224), 127.0.0.1 (not localhost), port-poll (not fixed sleep)
- Scores ALL articles per edition (not just unsaved) — fixes low-candidate problem
- Already-saved articles: scored but not re-inserted; logged as [already saved]
- call_anthropic() used for scoring (was incorrectly using kt_meta credentials)
- enrich_title_only_articles() + subprocess vps_push.py for post-insert steps
- Early gate removed (was blocking Apr 11 re-run when Apr 18 was scored)
- Results: Apr 18 edition: 75 candidates, 12→Feed; Apr 11: 70 candidates, 1→Feed, 5→Suggested
- All pushed to VPS

**Economist CDP monitoring**
- eco_scraper_sub.py: post-run ECONNREFUSED detection writes DOWN:HH:MM to kt_meta
- sync_last_run() returns eco_cdp_live based on kt_meta status
- Stats panel shows ⚠ CDP down on Economist LAST SCRAPED row when status=DOWN

**Economist ingestion analysis**
- Zero-days (Apr 7-11, Apr 16 morning): Chrome CDP port 9223 not binding — Chrome launch failing or profile locked
- Root cause of low AI picks: weekly pick only scored articles not already saved; most were bookmarked during week
- Fix: score all edition articles regardless of save status

**DB counts: ~920 articles (FT 280, Eco 362+13 AI picks, FA 169, Bloomberg 45, Other 46)**

**Session 58 agenda:**
1. FT unenriched backlog: ~30 pending title_only — trigger enrichment
2. Feed filter Stats/Bloomberg tab-switch stacking — still needs CSS fix
3. FA scraper: FA cookie renewal (expires 2026-05-23)
4. Economist bookmarks zero-days: investigate whether CDP port binding issue persists

### 16 April 2026 (Session 56)"""

content = content.replace(old_s56, new_s57, 1)

with open('/Users/alexdakers/meridian-server/NOTES.md', 'w') as f:
    f.write(content)
print("NOTES.md updated")
