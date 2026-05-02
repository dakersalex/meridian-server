I'm starting Session 78. The brief I'm pasting below is one I wrote myself
at the end of S77 (with Claude's help) — that's why it talks about "Alex"
in third person. Please proceed with the standard tool_search sequence
and read NOTES.md before doing anything else.

---

Before any prose response, run tool_search three times: filesystem write,
chrome browser tabs, shell bash. Only then read NOTES.md.

Meridian session start. Read NOTES.md and run the startup sequence per
"Session startup — CRITICAL ORDER".

**Read S77 main entry AND the S77 post-deploy addendum IN FULL** before
writing any code. The addendum (appended to the S77 entry) contains the
real context for this session — architectural decisions, diagnostic
findings, and the 13-item carry-over task list. Without it, this session
will start with the wrong framing.

S78 scope: SCRAPER DIAGNOSIS + ARCHITECTURE DECISION. Tier-2.
Diagnostic-first session, code-second. The goal is not to fix everything
in one go — it's to definitively answer the architectural question
"what do we do about Path 3 (Mac Playwright scrapers)?" and execute the
small fixes that don't depend on that decision.

Do NOT attempt all 13 carry-over items. Realistic scope for this session:
items 1–4 from the carry-over list. Items 5+ are S79+.

Time-box: 2h execution. 75% flag at 90 min. If 90 min hits and the
architectural decision isn't made, write up state and stop — Alex makes
the call in person, this session prepares the data.

**Pre-flight (mandatory, read-only):**

1. VPS /api/health/daily — should be ok=true OR ok=false on info/warning
   only.
2. extension_write_failures last 24h — should be 0–2. Column is
   \`timestamp\`, not \`saved_at_ms\`.
3. Three SHAs aligned. S77 closed at \`99e3c0a5\` with the diagnostic
   addendum committed. If the tree has advanced beyond that, that's
   fine — verify alignment, not the specific value.
4. Mac sync plist confirmed UNLOADED (Block 5 dropped it):
   launchctl list | grep com.alexdakers.meridian.wakesync — should
   return EMPTY.
5. Refresh plist confirmed loaded:
   launchctl list | grep com.alexdakers.meridian.refresh — should
   return the label.
6. Mac DB chmod 444 confirmed:
   stat -f '%Sp' ~/meridian-server/meridian.db — should show -r--r--r--.
7. Working tree state — expected clean (S77 + addendum committed).
   If dirty in production files (server.py, meridian.html, manifest.json),
   STOP — that's unexpected drift since S77 close.
8. Verify the addendum is in NOTES.md:
   grep -c "S77 post-deploy addendum" NOTES.md — should return 1.

**Carry-over task list (S78 scope: items 1–4 only):**

**Task 1 — Issue-coverage diagnostic (read-only, ~15 min)**

For the 70 articles in the Economist's 2 May 2026 issue
(/weeklyedition/2026-05-02), determine how many URLs are present in
the VPS DB.

Approach:
- Fetch /weeklyedition/2026-05-02 via web_fetch (or open in a tab and
  extract URLs via JS).
- Extract all article URLs from the issue page.
- Query DB: SELECT url FROM articles WHERE source='The Economist' AND
  saved_at > strftime('%s','2026-04-25')*1000 — get all recent Eco
  URLs.
- Compare: of N URLs in the issue, how many are in the DB?

Document the result. This number (\`X / N captured\`) is the definitive
answer to "is full-issue scraping worth restoring versus relying on RSS."

Decision threshold (Alex):
- If captured ≥ 70%: RSS coverage is good enough, retire Path 3.
- If captured ≤ 30%: full-issue scrape has real value, fix Path 3.
- Between: judgment call.

**Task 2 — Fix the Block 5 cron timing (~5 min)**

Per the addendum: Thursday 13:15 UTC fires 8h before the Eco issue
publishes at 21:00 UK Thursday. Should be Friday.

Fix:
```
ssh root@204.168.179.158 "crontab -l | sed 's|15 13 \* \* 4 /opt/meridian-server/venv|15 13 * * 5 /opt/meridian-server/venv|' | crontab -"
ssh root@204.168.179.158 "crontab -l | grep economist_weekly_pick"
```
(Verify the new entry shows \`15 13 * * 5\`.)

Update deploy/block5_cron_addition.txt to reflect the corrected schedule
+ rationale (Eco issue posts ~21:00 UK Thursday, so Friday 13:15 UTC
gives the Friday morning RSS pulls time to ingest the new issue before
the cron scores).

Commit the cron fix to deploy/block5_cron_addition.txt.

**Task 3 — Refresh Eco + FA cookies (~5 min per source)**

Regardless of Path 3 decision, both source profiles need fresh cookies:

For Economist:
- Open the economist_profile in a fresh Chromium via Playwright (or
  open Chrome with --user-data-dir=~/meridian-server/economist_profile).
- Navigate to economist.com.
- Manually log in. Confirm the session is active.
- Close the browser cleanly (no force-quit).

For FA:
- Same approach with fa_profile/.

Verify by checking Cookies file mtime — should be today's date after
this step:
```
stat -f '%Sm' ~/meridian-server/economist_profile/Default/Cookies
stat -f '%Sm' ~/meridian-server/fa_profile/Default/Cookies
```

This is a read-write task on the profile directories but does NOT
modify any code or database state.

**Task 4 — Path 3 architectural decision**

Based on Task 1's result, present Alex with three options + tradeoffs:

A. **Retire Path 3.** Accept RSS-only coverage. Drop the threading.Timer
   scheduler from server.py (single function removal, S79 work). Mac DB
   becomes purely a read-only mirror of RSS-fed VPS state. Cleanest
   architecture, accepts known coverage gap.

B. **Keep Path 3 on Mac.** Build a new launchd plist that triggers the
   Eco/FA scrapers on Mac (since cookies live there), then pushes
   results to VPS via API. Requires fixing the FA \`_discover_latest_issue\`
   parser, removing the hardcoded /105/2 fallback, fixing the section-
   page filter, and rebuilding the trigger now that wakesync is dead.
   Multi-session work but preserves full-issue capture.

C. **Migrate Path 3 to VPS.** Remote browser setup (xvfb + Playwright on
   VPS), cookie sync workflow ("log in remotely once a month"), profile
   directory migration. Most work, most aligned with Phase 2 vision.

Don't make this decision in S78 unless Alex explicitly does so. Surface
the data, document the tradeoffs, hand the call to Alex.

**Standing approvals (after Alex's go on each task):**

- Read-only DB queries on Mac and VPS
- ssh + crontab edits on VPS for Task 2 only
- Browser automation on local Mac for Task 3 (cookie refresh)
- ast.parse() and bash -n syntax checks on any code touched
- Reading any file under /opt/meridian-server/ via ssh

**Standing approvals (NOT given without explicit go):**

- ANY modification to server.py
- Running the existing Mac Playwright scrapers (Path 3) — they're broken
  and running them now risks Cloudflare flag or profile lock cascade
- ANY new code deploy via deploy.sh
- Restarting Flask on Mac or VPS

**Interrupt me for:**

- Pre-flight failure
- Working tree drift in production files since S77
- Task 1 result is genuinely ambiguous (e.g. 40-60% captured) — Alex
  decides
- 75% time-box flag (90 min)
- Any unexpected Cloudflare challenges or login failures during Task 3

**HARD RULES:**

- DO NOT run the existing Path 3 scrapers as part of "let's see if it
  still works" — that's S79 work after architectural decision is made
- DO NOT modify server.py in S78 — all server.py changes deferred to S79
- DO NOT attempt to backfill the May/June 2026 FA issue or 2 May Eco
  issue in S78 — backfill is the LAST step after fixes land
- DO NOT restart the δ→γ observation window — Alex makes that call

**Deliverables for S78 close:**

- NOTES.md S78 entry covering: pre-flight, Task 1 result with the
  X / N number, Task 2 cron fix confirmation, Task 3 cookie refresh
  confirmation, Task 4 architectural decision (or deferred state)
- deploy/block5_cron_addition.txt updated to reflect corrected
  Friday schedule
- Commit + push the above

Default if you don't know: STOP and ask Alex. He's at the desk
driving this. The discipline that kept Block 5 deploy clean
(separating sessions, refusing to mid-session scope creep) applies
fully here.

When done: working tree should be clean (everything committed +
pushed). Alex's first action when handed back will be \`git status\`
and \`git log --oneline -5\`.
