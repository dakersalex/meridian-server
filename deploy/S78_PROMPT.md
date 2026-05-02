Before any prose response, run tool_search three times: filesystem write,
chrome browser tabs, shell bash. Only then read NOTES.md.

Meridian session start. Read NOTES.md and run the startup sequence per
"Session startup — CRITICAL ORDER".

**Read these IN FULL before writing any code or making architectural decisions:**
- The S77 entry, including the post-S77 final addendum at the bottom of S77.
- The S77 final addendum is the most important context for this session.
  It captures (a) architectural decisions Alex made on 2 May, (b) diagnostic
  findings that emerged after S77 close, (c) the priority list with 9 items.

S78 scope: ARCHITECTURAL REVIEW + TARGETED FIXES. Tier-2.
This is NOT a sprint to fix everything. The S77 addendum surfaced ~9 items
ranging from cron-line tweaks to multi-session architectural rebuilds.
S78's first job is to **decide what's in scope for this session** based on
Alex's energy and time available. Then execute that subset.

Time-box: Alex chooses at session start (typical: 60–120 min).
75% flag at 75% of agreed length.

## Pre-flight (mandatory, read-only)

1. **VPS health.** `/api/health/daily` should be ok=true OR ok=false on
   info/warning only.
2. **extension_write_failures last 24h** should be 0–2. Column is
   `timestamp`.
3. **Three SHAs aligned.** S77 final commit was `99e3c0a5`. Alex may have
   committed the NOTES addendum after S77 — if so, SHAs will have advanced.
   What matters: Mac HEAD == VPS HEAD == origin/main.
4. **Working tree state.** Expect clean if Alex committed before S78, or
   dirty in well-understood ways (NOTES.md, tmp_*.* scratch files —
   gitignored). If dirty in production files (server.py, meridian.html,
   manifest.json) — STOP, that's unexpected drift.
5. **Block 5 systems still operating:**
   - launchctl list | grep com.alexdakers.meridian.wakesync should be EMPTY
     (unloaded, correct post-Block 5 state)
   - launchctl list | grep com.alexdakers.meridian.refresh should show
     the label (the Mac DB nightly refresh job)
   - stat -f '%Sp' ~/meridian-server/meridian.db should show "-r--r--r--"
     (chmod 444, read-only mirror)
6. **Did the nightly Mac refresh fire on Mon 4 May 04:00 Geneva?**
   Check ~/meridian-server/logs/refresh_mac_db.log for an entry from
   that date. If missing — that's the first new bug to investigate
   independent of scraper architecture.
7. **Did the Block 5 Thursday cron fire on 7 May 13:15 UTC?**
   ssh root@204.168.179.158 "tail -50 /var/log/meridian/economist_weekly.cron.log"
   Even though the timing is wrong (fires before Eco issue posts),
   the cron should still produce a log entry. If no entry — that's
   the second new bug.

## Standing approvals (read-only diagnostic, no Alex go needed)

- All read-only Mac and VPS queries (sqlite3 SELECT, ls, cat, grep, log
  show, stat, launchctl list, systemctl list-timers)
- ast.parse() and bash -n syntax checks on any code Claude drafts
- Reading any file under /opt/meridian-server/ via ssh
- Reading Mac logs in ~/meridian-server/logs/
- Reading kt_meta values

## Standing approvals (Tier-2 work, Alex must approve in chat first)

- crontab edits on VPS (e.g. fixing Block 5 cron timing)
- server.py patches via str_replace inside ~/meridian-server/ (NEVER edit
  VPS server.py directly — patch Mac, run deploy.sh)
- Running deploy.sh after a server.py patch
- Restart Flask via SSH (NEVER via the shell endpoint, that kills the
  process serving the request: ssh root@204.168.179.158
  'systemctl restart meridian')
- Manually triggering a single scraper run for testing, IF and ONLY IF
  Alex has explicitly chosen "verify scraper write path" as an in-scope
  task and explicitly approved the run

## HARD RULES

- DO NOT touch server.py, meridian.html, or manifest.json without
  explicit chat approval for that specific change. Show the proposed
  patch, get "yes do it," then patch + ast.parse + deploy.
- DO NOT make architectural decisions on Alex's behalf. The S77 addendum
  flags three architectural options for the Mac Playwright path
  (keep on Mac with fresh trigger / move to VPS / drop entirely).
  Those three options need Alex's input. Surface them with tradeoffs,
  let Alex choose.
- DO NOT run scrapers as casual experiments. If a scraper run is
  needed for verification, it's a deliberate setup with explicit
  approval — not "let's just try it."
- DO NOT execute deploy.sh without Alex's go on a specific patch.
- DO NOT push to origin/main without Alex's explicit confirmation.
- DO NOT add the δ→γ observation window back unless Alex explicitly
  decides it should restart now. The default is "still paused."

## Session structure

Recommend this flow (Alex can override):

**Phase 1: Pre-flight + scoping (10–15 min).**
Run the pre-flight checks. Surface results. Then ask Alex which
S78 priorities to tackle this session. The list from NOTES is:

1. Architectural review of Mac Playwright path
2. Fix Block 5 cron timing (Thu 13:15 UTC → Fri 13:15 UTC)
3. Fix _discover_latest_issue + remove hardcoded fallback in FA scraper
4. Add section-page filter to Eco scraper
5. Investigate the 30 April 23:58 Flask restart loop
6. Verify scraper write path with a controlled test
7. Refresh Eco/FA cookies if needed
8. Trust audit: spot-check capture rate against a recent week
9. (Deferred) Discovery features

Expected: Alex picks 2–4 items. Items 2 + 4 are 5-min wins. Item 1 is
the load-bearing decision that gates 3, 6, 7. Item 8 is meaningful
but only after 1–7 are settled.

**Phase 2: Architectural review of Playwright path (if in scope).**

The three options from S77 addendum:

- **A. Keep on Mac, fix the trigger.** Mac still has Chrome and cookies.
  Wakesync agent unloaded by Block 5. Need new launchd plist that just
  triggers the scrapers (read-only on Mac, push results to VPS via API).
  Pros: cookies stay where they are, simplest path. Cons: against the
  spirit of Block 5 (Mac as pure read-only mirror), keeps Mac as a
  load-bearing node.
- **B. Move to VPS with virtual-display Chrome.** Install xvfb-run +
  Playwright on VPS, copy profile directories, set up remote login
  flow. Pros: Phase 2 architectural cleanliness. Cons: high complexity,
  cookie management remote, more failure modes.
- **C. Drop Playwright, accept narrower coverage.** Rely on RSS +
  manual extension bookmarks. Pros: zero new infrastructure, simplest
  by far. Cons: confirmed under-captures issue-based publications
  (~14 of 70 Eco articles this week). Acceptable only if Alex decides
  comprehensive issue capture isn't worth the complexity.

Surface all three with tradeoffs. Let Alex decide. Don't recommend
unless Alex asks for a recommendation.

**Phase 3: Targeted fixes (if in scope).**

Items 2, 3, 4 are concrete patches. Item 5 is investigation. Item 6
is verification. Apply the deploy.sh + ast.parse + ssh restart pattern
for any server.py changes.

For item 2 (cron timing), the change is:
  `15 13 * * 4` → `15 13 * * 5` (Thursday → Friday)
  in deploy/block5_cron_addition.txt and on VPS root crontab.

**Phase 4: Trust audit (if in scope).**

Only if scrapers are demonstrably working post-fix. Pick a week,
manually open FT/Eco/FA pages from that week, identify articles
Alex would have read, check whether each landed in his Suggested
swim lane. Output: percentage capture rate per source, plus notes
on patterns of misses.

**Phase 5: Close.**

Update NOTES.md with S78 entry. Commit + push. Update S78_PROMPT.md
to reflect any items still open. Decide whether δ→γ window can
restart, and if so, set the new dates.

## Interrupt me for

- Pre-flight failure (especially items 5–7 — those are new since S77)
- Alex picking >5 items from the priority list (scope creep)
- Any production file modification surfacing
- Cookie expiry confirmed (Eco or FA login broken)
- 75% time flag hit
- Architectural decision being made without Alex's explicit input

## Default if you don't know

Stop and ask Alex. S78 is conversation-driven, not autonomous. The
S77 final addendum's "discipline that protected the deploy" note
applies here too: post-S77 is when discipline matters most because
the structure is gone.

## When done

- Working tree dirty in well-understood ways or fully committed
- NOTES.md S78 entry written
- S79 prompt drafted at deploy/S79_PROMPT.md if items remain open
- δ→γ status updated in NOTES (still paused / restart with new dates)
- Alex's first action when handed back: `git status` and
  `cat ~/meridian-server/NOTES.md | head -50`
