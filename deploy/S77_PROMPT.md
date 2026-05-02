Before any prose response, run tool_search three times: filesystem write,
chrome browser tabs, shell bash. Only then read NOTES.md.

Meridian session start. Read NOTES.md and run the startup sequence per
"Session startup — CRITICAL ORDER".

Read S76 main entry IN FULL before writing any code. Re-read PHASE_2_PLAN
§ 8 Block 5 only if the open server.py decision (see below) is being
acted on this session.

S77 scope: BLOCK 5 ATOMIC DEPLOY. Tier 1. P2-9 (deploy
economist_weekly_pick.py + install cron) followed by P2-10 (Mac write
authority dropped via deploy/block5_cutover.sh). This is the cutover
S76 prepped for. Alex is at the desk and ready to drive.

Time-box: 3h execution + 1h passive monitoring (per PHASE_2_PLAN § 9).
75% flag at 2h15. If the deploy hasn't substantively landed by then,
write up state and stop — do not push through.

Pre-flight (mandatory, read-only):
1. VPS /api/health/daily — should be ok=true OR ok=false on info/warning
   only (no Tier-3 conditions)
2. extension_write_failures last 24h — should be 0–2. Column is
   `timestamp`, NOT `saved_at_ms`.
3. Three SHAs aligned. S76 left them at `9de386de` but the working tree
   is dirty (S76 prep). If Alex committed the S76 deliverables since
   then, the SHAs will have advanced — that's expected. What matters
   is Mac HEAD == VPS HEAD == origin/main.
4. Mac sync plist confirmed currently loaded:
   launchctl list | grep com.alexdakers.meridian.wakesync
   (Note: `.wakesync`, NOT `.sync`. The S76 brief had the wrong label;
   this one is correct.)
5. Working tree state. Expected one of:
   (a) S76 deliverables committed and pushed: clean tree.
   (b) S76 deliverables still uncommitted: dirty tree showing
       deploy/, refresh_mac_db.sh, economist_weekly_pick.py, possibly
       NOTES.md modifications.
   Either is fine; neither blocks. If the tree is dirty in some other
   way (modified meridian.html, server.py, manifest.json), STOP — that's
   unexpected drift since S76 close.
6. Confirm deploy/BLOCK5_READY.md, deploy/block5_cron_addition.txt,
   deploy/block5_cutover.sh, deploy/block5_rollback.sh,
   deploy/com.alexdakers.meridian.refresh.plist, refresh_mac_db.sh,
   and economist_weekly_pick.py all exist.
7. Pool dry-run repeat. Re-run the S76 pool query to make sure the
   Economist 7-day pool is still ≥15:
   ssh root@204.168.179.158 "sqlite3 /opt/meridian-server/meridian.db
     \"SELECT COUNT(*) FROM articles WHERE source='The Economist'
     AND saved_at > strftime('%s','now')*1000 - 7*86400000;\""
   S76 saw 50 / 29 unscored. If it has dropped below 15 in the
   intervening days, STOP and surface — that's the δ→γ trigger.

The open server.py decision (BLOCK 5 PREREQUISITE — answer first):

Per BLOCK5_READY.md "Open question for Alex", before P2-10 runs you
need to decide what happens to ai_pick_economist_weekly() in server.py:
  - Option A (S76 recommendation): do nothing. Mac function fails
    silently on chmod-444 DB after cutover. Self-limiting, log-noisy.
  - Option B: edit server.py to early-return from
    ai_pick_economist_weekly() and from the scheduler tick at L2959.
    ~5 lines of change. Cleaner, but a server.py touch.

Surface this question to Alex BEFORE starting the deploy. If A: proceed
with the cutover sequence as written. If B: handle the server.py patch
as a Tier-2 prelude (str_replace patch via filesystem:write_file +
shell exec, ast.parse syntax check, deploy.sh push to VPS, verify Flask
restarts cleanly), THEN proceed to the cutover.

Standing approvals (only after Alex's go on the deploy):
- scp deliverables to VPS:
  - economist_weekly_pick.py to /opt/meridian-server/
- ssh + crontab modification on VPS to install the cron line from
  deploy/block5_cron_addition.txt
- Run the VPS-side dry-run:
  /opt/meridian-server/venv/bin/python3 economist_weekly_pick.py --dry-run
- Execute deploy/block5_cutover.sh on Mac
- Optional (Alex's call): cp the refresh plist to ~/Library/LaunchAgents/
  and launchctl load it
- Optional (Alex's call): bash refresh_mac_db.sh once for immediate
  Mac DB mirror

Standing approvals (read-only audit, no Alex go needed):
- Pre-flight queries on Mac and VPS
- ast.parse() and bash -n syntax checks
- Reading any file under /opt/meridian-server/ via ssh
- VPS log tails (/var/log/meridian/*.log)

Interrupt me for:
- Pre-flight failure
- Pool size <15
- Working tree drift in production files since S76 (server.py,
  meridian.html, manifest.json modified)
- Any failure during cutover steps 1-5 — the script is fail-loud,
  but if it aborts mid-way, STOP and run deploy/block5_rollback.sh
  before doing anything else
- VPS health going non-200 at any point during or after deploy
- 75% time flag (2h15)

HARD RULES:
- DO NOT skip the dry-run on VPS before installing the cron. The
  --dry-run is the last safety net before live API spend.
- DO NOT install the cron line without confirming the dry-run ran clean.
- DO NOT execute block5_cutover.sh until P2-9 has been verified
  (cron installed AND dry-run clean OR one real run successful).
- DO NOT modify deploy/block5_cutover.sh during the deploy. If a step
  needs adjustment, abort, edit, re-run from the top — the script's
  idempotency handles repeat runs.

Smoke verification after cutover lands (P2-10 done):
1. launchctl list | grep com.alexdakers.meridian.wakesync — should
   return EMPTY (unloaded)
2. ls ~/meridian-server/wake_and_sync.sh — should be missing
3. ls ~/meridian-server/archive/wake_and_sync_*.sh — should exist
4. ls ~/meridian-server/db_backups/meridian_pre_block5_*.db — should
   exist and pass integrity_check
5. curl https://meridianreader.com/api/health/daily — should be 200
6. If refresh plist installed: launchctl list | grep refresh — should
   show the label
7. If refresh_mac_db.sh ran: stat -f '%Sp' ~/meridian-server/meridian.db
   — should show 444

Deliverables for Alex's S77 close:
- BLOCK5_DEPLOYED.md (or amend BLOCK5_READY.md in place) with: the
  literal commands actually run, the timestamps, the snapshot path,
  the archive path, any deviations from the planned sequence
- NOTES.md S77 entry covering the deploy, the smoke verification
  results, and any operational notes
- The two-week δ→γ observation window starts NOW. Note the start
  date in NOTES.md so the next time someone reads it, they know
  when the decision is due.

Default if you don't know: STOP and ask Alex. He's at the desk
driving this — this is not an autonomous session. Block 5 is the
biggest single deploy of Phase 2 and the consequences of getting it
wrong are real (lost write authority, broken Mac Flask, broken VPS
ingestion). Ask first, act second.

When done: working tree should be either clean (everything committed
+ pushed) or dirty in well-understood ways (BLOCK5_DEPLOYED.md +
NOTES.md modifications staged for review). Alex's first action when
you hand back will be `git status` and `git log --oneline -5`.
