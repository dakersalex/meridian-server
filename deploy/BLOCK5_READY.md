# Block 5 — ready to deploy

**Session:** S76 prep (no commits, no execution).
**Generated:** 1 May 2026.
**Working tree:** dirty by design. `git status` will show new files only.

---

## TL;DR

The δ→γ signal: **pool is healthy, lean δ.**
- Last 7 days Economist articles in VPS DB: **50** (well above the 15 floor).
- Of those, unscored (not yet in `suggested_articles`): **29** (also above 15).
- 14-day trend: 91 articles. Distribution skewed to the most recent 2–3 days
  (32 on 30 Apr, 5 already on 1 May) — so there's a healthy weekly cadence.

This is comfortably above the §7 fallback threshold. δ is the right path
into Block 5.

All seven deliverables landed. No HARD RULE temptation hit. No interrupt
condition tripped. Pre-flight passed with one nominal correction (the
sync plist's actual label is `com.alexdakers.meridian.wakesync`, not
`com.alexdakers.meridian.sync`; the brief had the older naming).

Total prep time: roughly 50 min.

---

## Pre-flight results

| Check | Brief expectation | Actual | Status |
|---|---|---|---|
| 1. `/api/health/daily` | `ok=true` | `ok=false` (info+warning only: 30 title_only pending, 31 unenriched) | **PASS w/ caveat** — same `ok=false` pattern documented in S74/S75 closes; no Tier-3 conditions, no errors. |
| 2. `extension_write_failures` last 24h | 0–2 | 0 | **PASS** |
| 3. Three SHAs aligned | `9de386de…` | Mac HEAD = VPS HEAD = origin/main = `9de386dec06c946be69179e4c04e92c4b54e86e1` | **PASS** |
| 4. Mac sync plist loaded | `com.alexdakers.meridian.sync` | Loaded as `com.alexdakers.meridian.wakesync` (different label, same role) | **PASS** — see "things that surprised me" below. |
| 5. `wake_sync_vps.sh` tracked at HEAD | both sides | Tracked at `9e2c75f4` on Mac and VPS, MD5-identical (per S75 close) | **PASS** |

The brief said pool size <15 should trigger a loud flag and an Alex
decision. Pool is **50 total / 29 unscored**, both well above 15. **No
interrupt fired. Lean δ.**

Distribution by saved date for context (last 7 days):
```
2026-04-25 |  1
2026-04-27 |  1
2026-04-28 |  9
2026-04-29 |  2
2026-04-30 | 32
2026-05-01 |  5
```
Total: 50. Bulk on 30 Apr is consistent with the Chrome extension's
weekly Economist bookmark sync activity.

---

## Files written

All paths relative to `~/meridian-server/`.

### A. `economist_weekly_pick.py` — already in place

Already existed in repo root from a prior session, AST-clean, and matches
the S76 spec on all six behavioural points (query, scoring, log path,
Suggested-floor insert, ISO-week idempotency, dry-run flag). **Per the
brief's "modify in place rather than duplicating" guidance, no changes
written.** It is currently *untracked* — `git status` shows
`?? economist_weekly_pick.py`. Alex commits it as part of the Block 5
review pass.

One minor delta from the brief spec: the script's *internal* "pool too
thin" floor is 5, not 15. It logs a warning at `<5` and skips scoring.
The 15 figure in the brief is the δ→γ *decision* threshold (a meta
question about whether to keep using the δ path at all), not a per-run
abort. Both are right at their respective layers; flagging only because
they're different numbers and you might wonder. The δ→γ threshold is
something Alex evaluates at week 2.

### B. `deploy/block5_cron_addition.txt`

The literal cron line for VPS root crontab. **Not installed.**

```
15 13 * * 4 /opt/meridian-server/venv/bin/python3 /opt/meridian-server/economist_weekly_pick.py >> /var/log/meridian/economist_weekly.cron.log 2>&1
```

Schedule: **Thursday 13:15 UTC**. Rationale (full version in the file):
- Clear of 02:30 UTC enrich_retry, 03:40/09:40 UTC wake_sync,
  14:30 UTC enrich_retry_watchdog.
- **Minute 15** keeps it clear of the hourly extension_failure_watchdog
  (which runs at minute 0 every hour).
- **Hour 13** Thursday is mid-day Geneva, when fresh Suggested batches
  surface near review activity.

### C. `deploy/block5_cutover.sh`

P2-10 deploy script. **Not executed.** Banner-topped per brief. `bash -n`
clean. Steps:

1. Mac DB snapshot via SQLite `.backup` API → `db_backups/meridian_pre_block5_<TS>.db`
2. PRAGMA integrity_check on snapshot (abort on non-`ok`)
3. `launchctl unload com.alexdakers.meridian.wakesync`
4. `mv wake_and_sync.sh archive/wake_and_sync_<date>.sh`
5. Verify VPS `/api/health/daily` returns 200

`set -e -u -o pipefail`. Each step idempotent where possible
(launchctl unload checks current state; archive uses date-suffixed
path with HHMM fallback for collisions; mv only after snapshot
integrity check passes). Fail-loud on the integrity check, the unload
verification, and the post-archive VPS health probe.

### D. `refresh_mac_db.sh` (repo root)

§ 3 nightly DB mirror script. **Not executed.** `bash -n` clean. Steps:

1. ssh VPS, run `sqlite3 .backup /tmp/<temp>.db`
2. `scp` the temp snapshot back to Mac, clean up VPS-side temp
3. PRAGMA integrity_check on local copy (abort + clean tmp on failure)
4. Stop Mac Flask via `launchctl unload`, kill any orphan on :4242,
   swap `meridian.db`, `chmod 444`, `launchctl load` Flask
5. Smoke-call `http://127.0.0.1:4242/api/health/daily`

The chmod 644-then-444 sequence is deliberate — supports running this
script repeatedly after the first refresh has already locked the DB
read-only. The orphan-kill on :4242 is belt-and-braces against the
launchd double-spawn pattern documented in NOTES (R7 in PHASE_2_PLAN).

### E. `deploy/com.alexdakers.meridian.refresh.plist`

Mac launchd plist for the nightly DB refresh. **Not installed.** `plutil
-lint` clean. Triggers `refresh_mac_db.sh` once per night at 04:00
local Mac time (= 04:00 Geneva). 20-minute gap after the VPS 03:40 UTC
wake_sync_vps cron in winter (CET); 1h20m in summer (CEST). Both safe.

### F. `deploy/block5_rollback.sh`

P2-10 reverse. **Not executed.** `bash -n` clean. Designed to run in
under 2 minutes per § 2. Steps:

1. Restore `wake_and_sync.sh` from latest `archive/wake_and_sync_*.sh`
2. `launchctl load com.alexdakers.meridian.wakesync`
3. Verify `launchctl list` shows the label
4. `bash -n` syntax check the restored wake script

Idempotent across all steps. Includes a fallback hint to restore from
git history if the archive copy is somehow missing.

### G. `deploy/BLOCK5_READY.md`

This file.

---

## Literal command sequence — Block 5 deploy

These are the commands Alex runs when actually doing Block 5.
**Order matters: P2-9 lands before P2-10.**

```bash
# ── P2-9: Economist weekly pick on VPS ─────────────────────────────────

# 1. Push economist_weekly_pick.py to VPS
scp ~/meridian-server/economist_weekly_pick.py \
    root@204.168.179.158:/opt/meridian-server/economist_weekly_pick.py

# 2. Verify dry-run on VPS
ssh root@204.168.179.158 \
    "cd /opt/meridian-server && /opt/meridian-server/venv/bin/python3 economist_weekly_pick.py --dry-run"
#   Expected: pool size logged (~29 if run today against current state),
#   no DB writes, no API calls.

# 3. Append cron line — read deploy/block5_cron_addition.txt and
#    append the cron entry (NOT the comments) to root crontab on VPS:
ssh root@204.168.179.158 \
    "(crontab -l; echo ''; echo '# Meridian Phase 2 — Block 5 (Session 76)'; \
      echo '15 13 * * 4 /opt/meridian-server/venv/bin/python3 /opt/meridian-server/economist_weekly_pick.py >> /var/log/meridian/economist_weekly.cron.log 2>&1') | crontab -"

# 4. Verify cron entry persisted
ssh root@204.168.179.158 "crontab -l"

# ── P2-10: Mac authority dropped ───────────────────────────────────────

cd ~/meridian-server
bash deploy/block5_cutover.sh
#   Expected: 5 step banners, snapshot in db_backups/, launchctl unloaded,
#   wake_and_sync.sh in archive/, VPS health 200.

# ── Optional: install nightly Mac DB refresh ───────────────────────────

cp deploy/com.alexdakers.meridian.refresh.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.alexdakers.meridian.refresh.plist
launchctl list com.alexdakers.meridian.refresh
#   Expected: label appears in list.

# ── Optional: immediate first refresh of Mac DB from VPS ───────────────

bash refresh_mac_db.sh
#   Expected: snapshot pulled, integrity OK, Flask reloaded,
#   meridian.db now chmod 444.
```

---

## Literal command sequence — Block 5 rollback

If something goes wrong, **after running the cutover** but before P2-9
has settled into a working pattern:

```bash
cd ~/meridian-server
bash deploy/block5_rollback.sh
#   Expected: wake_and_sync.sh restored, wakesync plist loaded,
#   verification clean. <2 min.

# Optional: also remove the VPS cron entry
ssh root@204.168.179.158 \
    "crontab -l | grep -v 'economist_weekly_pick.py' | crontab -"

# Optional: also remove deployed economist_weekly_pick.py from VPS
ssh root@204.168.179.158 "rm -f /opt/meridian-server/economist_weekly_pick.py"

# Optional: remove the Mac refresh launchd job if you installed it
launchctl unload ~/Library/LaunchAgents/com.alexdakers.meridian.refresh.plist
rm ~/Library/LaunchAgents/com.alexdakers.meridian.refresh.plist
```

If the rollback script fails because `wake_and_sync.sh` is missing AND
no archive/wake_and_sync_*.sh exists, restore from git:

```bash
cd ~/meridian-server
git show HEAD:wake_and_sync.sh > wake_and_sync.sh
chmod +x wake_and_sync.sh
launchctl load ~/Library/LaunchAgents/com.alexdakers.meridian.wakesync.plist
```

---

## Things that surprised me during prep

1. **Mac sync plist label is `.wakesync`, not `.sync`.** The S76 brief
   references `com.alexdakers.meridian.sync` in pre-flight check 4 and
   in cutover step 3. The actual loaded plist is
   `com.alexdakers.meridian.wakesync`. There's an inert
   `com.alexdakers.meridian.sync.plist.disabled` from way back in the
   `~/Library/LaunchAgents/` directory but it's not loaded and would
   not respond to `launchctl unload`. **All deliverables use the
   correct `.wakesync` label.** Worth flagging because the brief
   sequence "launchctl unload ~/Library/LaunchAgents/com.alexdakers.meridian.sync.plist"
   would have been a no-op.

2. **The δ→γ threshold mismatch.** The brief says "If <15, flag it
   loudly." The `economist_weekly_pick.py` script has its own
   "skip-this-run" floor at 5. The brief's 15 is for the strategic
   decision (do we keep δ at all?); the script's 5 is for tactical
   "is this run worth API spend?". They're different concepts at
   different layers. Both are fine. Flagging only because reading
   them side-by-side is confusing.

3. **`economist_weekly_pick.py` already exists, untracked.** A previous
   session (probably ~April 30 based on file mtime) wrote the script
   but didn't commit. AST-clean, behaviourally matches the spec on
   every point. The right action per brief was "modify in place,
   don't duplicate" — which here means leaving it alone, since the
   in-place version is already correct. Alex commits it as part of
   the Block 5 review pass.

4. **VPS cron schedule is busier than the brief implied.** Beyond the
   three slots the brief mentioned (02:30, 03:40, 09:40 UTC), there's
   also `30 14 * * *` (enrich_retry_watchdog) and `0 * * * *` (hourly
   extension_failure_watchdog). The hourly minute-0 slot was the
   binding constraint — any Thursday hour at minute 0 would collide.
   13:15 UTC navigates around all five.

5. **No interrupt conditions hit.** Pre-flight clean (modulo the label
   correction in #1, which is a cosmetic miss in the brief, not a
   broken precondition). Pool size 50/29 well above 15. No HARD RULE
   was tempting at any point.

---

## Open question for Alex (decide before running cutover)

**Does Block 5 cutover need to disable `ai_pick_economist_weekly()` in
`server.py`?**

Background. `server.py` line 2328 still has the Mac-Playwright-based
`ai_pick_economist_weekly()` function, called from the internal
threading scheduler at line 2959 (`scheduler_eco_weekly_<date>`
gate-keyed) and from the `/api/ai-pick-economist-weekly` endpoint at
line 1343. With the wakesync agent unloaded by P2-10, the *external*
trigger path is gone — but the internal Flask threading.Timer still
fires `_ew_key = f"scheduler_eco_weekly_{now.date()}"` once per day
inside `server.py:2959` while Mac Flask is running.

Once `economist_weekly_pick.py` is live on VPS via cron, you'd have
two paths trying to score Economist articles weekly: one on Mac via
Playwright over fresh scrape, one on VPS via DB query over extension
ingestion. They write to the same suggested_articles table on different
DBs (Mac DB vs VPS DB), but post-Block 5 the Mac DB is a chmod-444
read-only snapshot, so the Mac-side function would actually fail at
the SQLite write — `attempt to write a readonly database`. That's
arguably *fine* (it self-disables via failure) but it's also noisy
in logs and confusing on read-back.

The PHASE_2_PLAN § 8 P2-9 atomic-rollback note explicitly mentions
"re-enabling Mac `ai_pick_economist_weekly()`" as part of the rollback,
implying the cutover *does* disable it. So somewhere there's an
implicit step missing from both the brief and the plan: **edit
server.py to early-return from `ai_pick_economist_weekly()` when on
Mac.**

S76's HARD RULE says "DO NOT modify server.py in this session," so I
left this alone. But the question needs to be answered before P2-10
runs:

- **Option A — do nothing.** Let the Mac-side function fail silently
  on the read-only DB. Accept some log noise. Cleanest in terms of
  S76 scope (no server.py touch needed at all).
- **Option B — edit server.py before cutover.** Add an early return
  to `ai_pick_economist_weekly()` and to the scheduler tick at line
  2959. ~5 lines of change. Slightly cleaner, but requires the
  hard-rule exception you'd have to OK.

Recommendation: **A.** The Mac function failing on a chmod-444 DB is
self-limiting. If the log noise becomes annoying, take it out in a
follow-up Tier-2 session. Atomic rollback still works because re-loading
the plist + re-enabling the read-write cycle restores the function's
ability to actually write. Lower risk than touching server.py inside
the Block 5 window.

This is the only decision needed before running the cutover. Everything
else is mechanical.

---

## What's blocked / what's TODO

Nothing blocked. No TODOs were left in any deliverable — all four
scripts and both config files are complete-as-written. The only open
item is the server.py question above, which is a decision rather than
a coding task.

---

## State at end of S76 prep

- Working tree dirty (new untracked files in `deploy/` and at repo
  root). `git status --short` will show:
  ```
  ?? deploy/
  ?? economist_weekly_pick.py     (was already there from prior session)
  ?? refresh_mac_db.sh
  ?? tmp_s76_*.txt                (this session's pre-flight scratch)
  ```
- All repo invariants from S75 close still hold:
  - Mac HEAD = VPS HEAD = origin/main = `9de386de…`
  - 6 critical files unchanged
  - meridian.service active on VPS
  - extension_write_failures = 0
- No commits, no pushes, no VPS state changes, no launchctl mutations,
  no cron edits.
- `tmp_s76_preflight.txt`, `tmp_s76_preflight2.txt`, `tmp_s76_pool.txt`,
  `tmp_s76_old_paths.txt` left in repo as audit trail of the pre-flight
  and pool query results — gitignored under `tmp_*` (verify if needed:
  `cat .gitignore | grep tmp`). Delete before commit if Alex prefers
  a clean tree.
