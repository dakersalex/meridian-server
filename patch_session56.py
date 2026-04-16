with open('/Users/alexdakers/meridian-server/NOTES.md', 'r') as f:
    content = f.read()

# Update header
content = content.replace(
    "Last updated: 16 April 2026 (Session 56 start — NOTES cleanup, MCP startup fix)",
    "Last updated: 16 April 2026 (Session 56 — AI pick overhaul, FA scoring fixes, threshold changes)"
)

# Update outstanding issues
old_issues = """### 🔴 Session 56 — do first (in order)
1. **Remove FA most-read from AI pick** — superseded by /search
   Verify: `grep "FA_MOST_READ" ~/meridian-server/server.py`
2. **Per-source caps for AI pick** — FT=30, FA=15, Economist=20
   Verify: `grep "PER_SOURCE_CAPS" ~/meridian-server/server.py`
3. **Verify FA /search working** — first full run was interrupted by Flask restart; check today's 06:15 logs
4. **Economist delivery gaps** — zero-days on 04-08, 04-11, 04-13
5. **FT unenriched backlog** — 59 pending title_only articles
6. **API credit indicator** — consider failure-rate proxy in stats panel
7. **wake_and_sync.sh push redundancy** — Flask auto-pushes now; explicit vps_push.py call redundant for articles"""

new_issues = """### 🔴 Session 57 — do first
1. **Economist delivery gaps** — zero-days on 04-08, 04-11, 04-13; check bookmarks scraper logs
2. **FT unenriched backlog** — 59 pending title_only articles; trigger enrichment run
3. **Feed filter bar visible on Suggested tab** — `.feed-controls` hide logic exists but top filter row still shows; needs DOM inspection to find correct element to hide
4. **API credit indicator** — consider failure-rate proxy in stats panel
5. **wake_and_sync.sh push redundancy** — Flask auto-pushes now; explicit vps_push.py call redundant for articles"""

content = content.replace(old_issues, new_issues, 1)

# Update AI pick section
old_ai = """### Candidate filtering — PENDING FIX Session 56
- **Current (broken):** single 50-article cap across all sources sorted by pub_date
  - FT dominates; FA with blank pub_dates sorted to bottom
- **Pending:** per-source caps — FT=30, FA=15, Economist=20
  - Check: `grep "PER_SOURCE_CAPS" ~/meridian-server/server.py`"""

new_ai = """### Candidate filtering (fixed Session 56)
- 36h filter applied FIRST, THEN prompt built — previously prompt was built before filter causing Sonnet to score all 100+ pre-filter candidates instead of the 15-20 post-filter ones
- No pre-scoring cap — score all candidates within 36h window (cap was removing potential high scorers)
- max_tokens: 6000 → 500 (flat integer array only needs ~50 tokens output)
- Prompt now uses dynamic N: "Respond with EXACTLY {N} integers" with N-length example
- Per-source feed thresholds: FA ≥7 → Feed, FT/Economist ≥8 → Feed"""

content = content.replace(old_ai, new_ai, 1)

# Update sources section
old_sources = """3. **Foreign Affairs most-read** — PENDING REMOVAL Session 56
   - Superseded by /search; no pub_date, title-only scoring
   - Check: `grep "FA_MOST_READ" ~/meridian-server/server.py`"""

new_sources = """3. **Foreign Affairs most-read** — REMOVED Session 56
   - Superseded by /search which provides pub_dates + standfirst"""

content = content.replace(old_sources, new_sources, 1)

# Add Session 56 to build history
old_history = "### 15 April 2026 (Session 55)"
new_session = """### 16 April 2026 (Session 56)

**AI pick pipeline — major fixes**
- Root cause of wrong score count: prompt was built BEFORE 36h filter → Sonnet scored all ~100 pre-filter candidates, returned 100 scores, routing used positions 0-N for N filtered candidates (wrong scores)
  Fix: moved filter before prompt build — Sonnet now receives exactly N filtered candidates
- max_tokens 6000 → 500 (flat integer array needs ~50 tokens, not 6000)
- Prompt now uses dynamic N: `EXACTLY {len(candidates)} integers` with matching example
- Pre-scoring caps removed entirely — score all candidates within 36h (caps were dropping potential high-scorers)
- FA most-read removed from AI pick — superseded by /search
- `/podcasts/` added to FA SKIP_PREFIXES

**FA scoring threshold**
- FA feed threshold lowered: >=7 → Feed (was >=8), FT/Economist stays >=8
- Rationale: FA analytical essays rarely hit 9-10 (reserved for breaking events); 7 = "high-quality geopolitical analysis"
- Promoted all historical FA 7+ suggested articles to Feed (Mac + VPS)

**FA pub_date fixes**
- Fetched actual pub_dates for blank-dated FA Feed articles via Playwright
- The Iran Imperative: 2026-04-02, The Iran Shock: 2026-04-06, The Real War for Iran's Future: 2026-03-31
- Deleted podcast article incorrectly ingested as Feed article

**Suggested tab UI**
- Added padding-bottom:14px to suggested cards — was missing spacing between buttons and next card

**Chrome MCP startup**
- Documented: clicking extension icon wakes service worker
- Added Step 0 to session startup checklist in NOTES.md

**DB counts: ~890 articles (FT ~267, Eco ~362, FA ~170, Bloomberg 45, Other 46)**

### 15 April 2026 (Session 55)"""

content = content.replace(old_history, new_session, 1)

with open('/Users/alexdakers/meridian-server/NOTES.md', 'w') as f:
    f.write(content)
print("NOTES.md updated")
