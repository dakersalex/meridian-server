import re

with open('/Users/alexdakers/meridian-server/NOTES.md', 'r') as f:
    content = f.read()

old_issues = """### 🔴 Session 56 — do first
1. **FA AI picks missing pub_date** — FA most-read scraper doesn't extract dates; articles fall back to saved_at in swim lanes
2. **Economist delivery gaps** — 3 zero-days (04-08, 04-11, 04-13); check bookmarks scraper logs + session health
3. **FT unenriched backlog** — 59 pending (includes 38 backfilled title_only articles); trigger enrichment
4. **API credit indicator** — no programmatic endpoint; consider failure-rate proxy in stats panel
5. **wake_and_sync.sh push redundancy** — now that Flask auto-pushes after sync, the explicit vps_push.py call in wake_and_sync.sh is redundant for articles (but still needed for newsletters/images/interviews); review and simplify"""

new_issues = """### 🔴 Session 56 — do first (in order)
1. **Remove FA most-read from AI pick** — superseded by /search; patch written in save_backfill.py but NOT yet executed (MCPs died). Check server.py state and apply.
2. **Per-source caps for AI pick** — replace single 50-article cap with FT=30, FA=15, Economist=20; patch written but NOT yet executed. Apply after item 1.
3. **Verify FA /search AI pick working** — added at end of session 55, deployed, but full test run was interrupted by Flask restart mid-execution. Check logs from 06:15 run today.
4. **Economist delivery gaps** — 3 zero-days (04-08, 04-11, 04-13); check bookmarks scraper logs + session health
5. **FT unenriched backlog** — 59 pending (includes 38 backfilled title_only articles); trigger enrichment
6. **API credit indicator** — no programmatic endpoint; consider failure-rate proxy in stats panel
7. **wake_and_sync.sh push redundancy** — Flask now auto-pushes after sync; explicit vps_push.py in wake_and_sync.sh redundant for articles (still needed for newsletters/images/interviews)

### ⚠️ Session 55 cut off mid-execution (Claude infrastructure error)
The following were written but NOT deployed/executed when MCPs died:
- `save_backfill.py` contains regex-based patch to remove FA most-read + add per-source caps
- Check whether server.py already has these changes or not before re-applying
- `grep "FA most-read removed\\|Per-source caps" ~/meridian-server/server.py` to check state"""

content = content.replace(old_issues, new_issues, 1)

# Also update the AI pick section to document FA /search and pending changes
old_ai_sources = """2. **Foreign Affairs most-read** — `foreignaffairs.com/most-read`
   - Plain HTTP fetch, no auth needed
   - pub_date: still blank ← outstanding fix needed"""

new_ai_sources = """2. **Foreign Affairs /search (most recent)** — `foreignaffairs.com/search`
   - Playwright, fa_profile/, headless (added Session 55)
   - Extracts pub_date from card text ("April 15, 2026" → YYYY-MM-DD) ✅
   - Extracts standfirst for better scoring accuracy ✅
   - Returns ~28 most recent FA articles per run
3. **Foreign Affairs most-read** — PENDING REMOVAL (Session 56 item 1)
   - Superseded by /search which provides pub_dates + standfirst
   - Currently still in code — remove at Session 56 start"""

content = content.replace(old_ai_sources, new_ai_sources, 1)

with open('/Users/alexdakers/meridian-server/NOTES.md', 'w') as f:
    f.write(content)
print("NOTES.md updated")
