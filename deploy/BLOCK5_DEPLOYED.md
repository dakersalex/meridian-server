# Block 5 — DEPLOYED

**Session:** S77 (2 May 2026)
**Status:** Both P2-9 and P2-10 landed cleanly. Both optional follow-ons (refresh launchd plist install + immediate Mac DB mirror) also landed.
**Total execution time:** ~30 min (well inside the 3h budget per PHASE_2_PLAN § 9).
**δ→γ observation window:** Opens 2 May 2026, decision date **16 May 2026** (week 2 per § 7).

---

## Pre-flight (all PASS)

| # | Check | Expected | Actual | Status |
|---|---|---|---|---|
| 1 | VPS `/api/health/daily` | `ok=true` OR info/warning only | `ok=true`, alerts=[], `ingested_24h=19` | **PASS — cleaner than S76** (which had info/warning) |
| 2 | `extension_write_failures` last 24h | 0–2 | 0 | **PASS** |
| 3 | Three SHAs aligned | Mac=VPS=origin/main | All three at `39c83ce6` | **PASS** — exactly the value in the brief |
| 4 | Mac wakesync plist loaded | `com.alexdakers.meridian.wakesync` | Present | **PASS** |
| 5 | Working tree clean | No drift in production files | Empty `git status --short` | **PASS** |
| 6 | All 7 deliverables present | Mac AND VPS | All 7 present, byte-identical | **PASS** |
| 7 | Pool size ≥ 15 (δ→γ floor) | ≥ 15 | 50 total / 29 unscored, last 7 days | **PASS — well above floor, lean δ** |

One pool-query slip during pre-flight: first attempt used a wrong column name (`s.article_id`) on `suggested_articles`. The schema joins by `s.url`, not `s.article_id`. Recovered immediately by reading the `.schema` and re-running. Result was identical to S76's pool count (50 / 29).

The exact corrected pool query (via SQL file, scp, ssh execute):

```sql
-- /tmp/s77_pool.sql (scp'd to VPS, then sqlite3 < it)
SELECT 'TOTAL_7D='||COUNT(*) FROM articles
WHERE source='The Economist'
  AND saved_at > strftime('%s','now')*1000 - 7*86400000;

SELECT 'UNSCORED_7D='||COUNT(*) FROM articles a
WHERE a.source='The Economist'
  AND a.saved_at > strftime('%s','now')*1000 - 7*86400000
  AND NOT EXISTS (SELECT 1 FROM suggested_articles s WHERE s.url=a.url);
```

Result: `TOTAL_7D=50`, `UNSCORED_7D=29`.

## Open decision (resolved)

Q: Disable `ai_pick_economist_weekly()` in `server.py` before cutover?
**A: Option A — do nothing.** Per S76 recommendation in `BLOCK5_READY.md`. Mac function will fail silently on the chmod-444 DB; self-limiting; no server.py touch needed. If log noise becomes annoying, take it out in a follow-up Tier-2.

Decision flagged to Alex via `ask_user_input_v0` before any deploy step ran.

---

## Literal commands run (verbatim, copy-paste-ready)

The commands below are **exactly** what executed during S77, minus the bash bookkeeping (`OUT=...`, `set +e`, output redirection to tmp files). Copy any of these directly into a Terminal to re-execute.

### P2-9 step 1 — scp economist_weekly_pick.py to VPS (parity)

```bash
scp -o ConnectTimeout=8 \
    /Users/alexdakers/meridian-server/economist_weekly_pick.py \
    root@204.168.179.158:/opt/meridian-server/economist_weekly_pick.py

# Parity verification:
echo "Mac: $(wc -c < /Users/alexdakers/meridian-server/economist_weekly_pick.py) bytes"
ssh -o ConnectTimeout=8 root@204.168.179.158 \
    "wc -c < /opt/meridian-server/economist_weekly_pick.py" \
    | awk '{print "VPS: " $1 " bytes"}'
```

Result: `Mac: 11806 bytes`, `VPS: 11806 bytes`.

### P2-9 step 2 — VPS-side dry-run (the safety net)

```bash
ssh -o ConnectTimeout=8 root@204.168.179.158 \
    "cd /opt/meridian-server && /opt/meridian-server/venv/bin/python3 economist_weekly_pick.py --dry-run"
```

Result: pool size 25 candidates logged, no DB writes, no API calls, exit 0. (Pool-size delta from pre-flight 29 → 25 is the script's own filter being slightly tighter; both well above the 5-article internal floor.) One harmless `DeprecationWarning` on `datetime.utcnow()` — cosmetic.

### P2-9 step 3 — Append cron line to VPS root crontab

```bash
ssh -o ConnectTimeout=8 root@204.168.179.158 \
    "(crontab -l; echo ''; echo '# Meridian Phase 2 — Block 5 (Session 76 prep, S77 deploy)'; echo '15 13 * * 4 /opt/meridian-server/venv/bin/python3 /opt/meridian-server/economist_weekly_pick.py >> /var/log/meridian/economist_weekly.cron.log 2>&1') | crontab -"
```

The cron entry that landed (verbatim):

```
# Meridian Phase 2 — Block 5 (Session 76 prep, S77 deploy)
15 13 * * 4 /opt/meridian-server/venv/bin/python3 /opt/meridian-server/economist_weekly_pick.py >> /var/log/meridian/economist_weekly.cron.log 2>&1
```

### P2-9 step 4 — Verify cron persisted (one and only one match)

```bash
ssh -o ConnectTimeout=8 root@204.168.179.158 "crontab -l"
ssh -o ConnectTimeout=8 root@204.168.179.158 "crontab -l | grep -c economist_weekly_pick"
```

Result: existing 5 entries unchanged + the new line. `grep -c` returned `1`.

### P2-10 — Cutover

```bash
cd /Users/alexdakers/meridian-server
bash deploy/block5_cutover.sh
```

All 5 steps reported clean from the script:

- **Step 1/5** — Mac DB snapshot via `.backup`: `db_backups/meridian_pre_block5_20260502_0913.db` (37,969,920 bytes)
- **Step 2/5** — `PRAGMA integrity_check`: `ok`
- **Step 3/5** — `launchctl unload com.alexdakers.meridian.wakesync`: confirmed unloaded
- **Step 4/5** — Archive: `wake_and_sync.sh` → `archive/wake_and_sync_20260502.sh` (5405 bytes)
- **Step 5/5** — VPS health: HTTP 200, `ok=true`, `ingested_24h=19`, `last_rss_pick=2026-05-02`

Started: `2026-05-02 09:13:42 CEST` · Completed: same minute (~5 seconds elapsed in-script).

### Optional follow-on A — Mac refresh launchd plist install

```bash
cp /Users/alexdakers/meridian-server/deploy/com.alexdakers.meridian.refresh.plist \
   /Users/alexdakers/Library/LaunchAgents/com.alexdakers.meridian.refresh.plist

plutil -lint /Users/alexdakers/Library/LaunchAgents/com.alexdakers.meridian.refresh.plist
# → OK

launchctl load /Users/alexdakers/Library/LaunchAgents/com.alexdakers.meridian.refresh.plist

launchctl list | grep com.alexdakers.meridian.refresh
# → -    0    com.alexdakers.meridian.refresh
```

Plist installed at 09:26 CEST. Schedule: 04:00 Geneva nightly.

### Optional follow-on B — Immediate Mac DB mirror (with deviation)

**Deviation from planned sequence — see "Deviations" below.** First attempt:

```bash
# FIRST ATTEMPT — failed
cd /Users/alexdakers/meridian-server
nohup bash refresh_mac_db.sh > tmp_s77_refresh.txt 2>&1 &
```

Bridge `fetch` to invoke this returned `Failed to fetch` immediately. The partial log (`tmp_s77_refresh.txt`) showed the script had completed steps 1–3 (snapshot, scp, integrity_check) but aborted at step 4 (Flask unload) — leaving an orphaned `meridian.db.refresh.79051` on disk and the original Mac DB untouched at 644.

Recovery — switched to launchd-triggered on-demand run, which is independent of the bridge:

```bash
# RECOVERY PATH — succeeded
rm -f /Users/alexdakers/meridian-server/meridian.db.refresh.79051
mkdir -p /Users/alexdakers/meridian-server/logs
: > /Users/alexdakers/meridian-server/logs/refresh_mac_db.log
launchctl start com.alexdakers.meridian.refresh
```

`launchctl start` is fire-and-forget; the job runs in its own process tree, so bridge survival is irrelevant. Job completed successfully — log shows full 5-step run from 09:36:53 → 09:37:08 CEST (~15 seconds total).

Final state:
- Mac DB swapped to VPS mirror (47,927,296 bytes — same as VPS source)
- Permissions: `-r--r--r--` (chmod 444) ✓
- Flask reloaded, HTTP 200 on smoke
- No orphan `.refresh.*` files left behind

One note from the log: `Unload failed: 5: Input/output error` on the launchctl unload step. This is a known macOS quirk for KeepAlive=true plists; the script handles it via the `|| echo "(already unloaded — continuing)"` fallback. The orphan-PID-on-:4242 belt-and-braces path then runs and kills PID 79061 cleanly. Worth flagging — the log line *looks* alarming but is actually expected behavior.

---

## Smoke verification (all PASS)

Per the S77 brief's mandatory smoke battery — verbatim commands and results:

```bash
# Smoke 1: wakesync unloaded
launchctl list | grep com.alexdakers.meridian.wakesync
# → empty (exit 1) ✓

# Smoke 2: wake_and_sync.sh missing from repo root
ls /Users/alexdakers/meridian-server/wake_and_sync.sh
# → ls: ...: No such file or directory ✓

# Smoke 3: archive present
ls -la /Users/alexdakers/meridian-server/archive/wake_and_sync_*.sh
# → -rw-r--r--@ 1 alexdakers staff 5405 Apr 19 11:53 archive/wake_and_sync_20260502.sh ✓

# Smoke 4: snapshot exists + integrity_check
ls -la /Users/alexdakers/meridian-server/db_backups/meridian_pre_block5_*.db
sqlite3 /Users/alexdakers/meridian-server/db_backups/meridian_pre_block5_20260502_0913.db \
    "PRAGMA integrity_check;"
# → 37,969,920 bytes; integrity ok ✓

# Smoke 5: VPS health 200
curl -s -o /tmp/s77_health.json -w '%{http_code}' https://meridianreader.com/api/health/daily
# → 200 ✓

# Bonus — refresh plist installed
launchctl list | grep com.alexdakers.meridian.refresh
# → present ✓

# Bonus — Mac DB perms 444
stat -f '%Sp' /Users/alexdakers/meridian-server/meridian.db
# → -r--r--r-- ✓

# Bonus — Mac Flask still LISTEN on :4242
lsof -i :4242 -P -n | grep LISTEN
# → Python 79241 alexdakers ... TCP *:4242 (LISTEN) ✓
```

Mac Flask remained up throughout: PID 764 → killed during refresh (orphan-kill path) → respawned by launchd → PID 79241.

---

## Deviations from planned sequence

1. **`refresh_mac_db.sh` invocation method.** The brief / `BLOCK5_READY.md` lists `bash refresh_mac_db.sh` as the expected command. First attempt via shell bridge died on the bridge fetch (likely because the bridge call needs to return *before* Flask is killed in step 4 of the script, and on this Mac the handshake didn't survive). Recovery via `launchctl start com.alexdakers.meridian.refresh` worked cleanly because the launchd-spawned process is independent of the bridge.

   **Net effect:** identical to the planned outcome (Mac DB now mirrors VPS, chmod 444). No data loss; no Flask downtime beyond the planned swap window. The deviation is an invocation-mechanism choice, not a behavioral change.

   **Implication for future on-demand refreshes:** prefer `launchctl start com.alexdakers.meridian.refresh` over `bash refresh_mac_db.sh` when Flask-via-bridge is the only shell path. The launchd-job route also writes structured logs to `~/meridian-server/logs/refresh_mac_db.log`, which is useful for audit.

That's the only deviation. Everything else followed the literal sequence in `BLOCK5_READY.md`.

---

## Working tree state at end of S77

`git status --short`:

```
 D wake_and_sync.sh
?? archive/
?? deploy/
?? economist_weekly_pick.py
?? refresh_mac_db.sh
?? deploy/BLOCK5_DEPLOYED.md
?? tmp_s77_*.{txt,sh,sql,py}
?? logs/refresh_mac_db.log
```

Recommended single commit at S78 opener:

```bash
cd /Users/alexdakers/meridian-server
git rm wake_and_sync.sh
git add deploy/ economist_weekly_pick.py refresh_mac_db.sh archive/wake_and_sync_20260502.sh
git add NOTES.md
git commit -m "Session 77 — Block 5 deploy: P2-9 cron + P2-10 cutover landed; refresh job installed; Mac DB mirrored read-only"
git push origin main
```

`tmp_s77_*` and `logs/refresh_mac_db.log` are gitignored under existing `tmp_*` and `logs/` patterns; left as audit trail.

VPS state to be reconciled after this commit:
- VPS `/opt/meridian-server/economist_weekly_pick.py` is byte-identical to Mac (post-scp parity check)
- VPS crontab has the new line — not in any tracked file. The crontab itself isn't versioned in this repo; the cron *recipe* is at `deploy/block5_cron_addition.txt`, which gets committed in the push above.

---

## What to watch over the next 2 weeks

**δ→γ observation window: 2 May 2026 → 16 May 2026.**

Per PHASE_2_PLAN § 7, decide at week 2:
- If candidate pool stays ≥ 15 unscored Economist articles per week AND quality of picks is acceptable → **stay on δ**.
- If pool dries up OR quality drops → **fall back to γ** (re-enable the Mac Playwright job as a charter § 9 named exception). Note the rollback path is `deploy/block5_rollback.sh` if Mac sync needs to be re-loaded; the Mac Playwright path is independent of that.

First scheduled cron run: **Thursday 7 May 2026 13:15 UTC**. Watch `/var/log/meridian/economist_weekly.cron.log` and the Feed afterward.

```bash
# Useful inspection commands for the week-2 decision:
ssh root@204.168.179.158 "tail -100 /var/log/meridian/economist_weekly.cron.log"
ssh root@204.168.179.158 "sqlite3 /opt/meridian-server/meridian.db \"SELECT COUNT(*), AVG(score) FROM suggested_articles WHERE source='The Economist' AND added_at > strftime('%s','now')*1000 - 14*86400000;\""
```

Second scheduled run: **Thursday 14 May 2026 13:15 UTC** — by which point the week-2 decision is informed by 2 real cron runs of data.

First nightly Mac DB refresh: **Monday 4 May 2026 04:00 Geneva** (CEST = 02:00 UTC). Log will land at `~/meridian-server/logs/refresh_mac_db.log`. Watch for clean 5-step output:

```bash
cat /Users/alexdakers/meridian-server/logs/refresh_mac_db.log
```

---

## Rollback (in case it's ever needed — copy-paste-ready)

If something breaks during the observation window and Block 5 needs to be reverted:

```bash
cd /Users/alexdakers/meridian-server
bash deploy/block5_rollback.sh
# Restores wake_and_sync.sh from archive/, re-loads wakesync plist, verifies. <2 min.

# Optional: also remove the VPS cron entry
ssh root@204.168.179.158 \
    "crontab -l | grep -v 'economist_weekly_pick.py' | crontab -"

# Optional: also remove deployed economist_weekly_pick.py from VPS
ssh root@204.168.179.158 "rm -f /opt/meridian-server/economist_weekly_pick.py"

# Optional: remove the Mac refresh launchd job
launchctl unload /Users/alexdakers/Library/LaunchAgents/com.alexdakers.meridian.refresh.plist
rm /Users/alexdakers/Library/LaunchAgents/com.alexdakers.meridian.refresh.plist

# Optional: restore Mac DB to writable (if rolling back fully)
chmod 644 /Users/alexdakers/meridian-server/meridian.db
```

Note: rolling back P2-10 (re-loading wakesync) does NOT automatically restore Mac write authority — the Mac DB is still chmod 444 from the refresh. If the rollback intent is "get back to Phase 1 fully", also run `chmod 644` on the DB. If the intent is "pause Block 5 but keep VPS canonical", leave the DB at 444.

---

## Carry-over to S78

1. **Commit the working tree** per the split above. Single S78 opener task, ~5 min.
2. **First Thursday cron run** — manual review at Mon 5 / Tue 6 May to look at what the cron picked up Thursday 7 May.
3. **First nightly refresh log** — Monday 4 May 2026 04:00 Geneva. Inspect `~/meridian-server/logs/refresh_mac_db.log` at S78 for clean 5-step output.
4. **L3850 `max_tokens=1000` review** — still open from S69. Low priority.
5. **R9 — git-history cleanup sandbox** at `~/meridian-server-sandbox` (S63). Must be decided before Phase 3.
6. **`ai_pick_economist_weekly()` log-noise cleanup** (Option B retroactively, Tier-2) — deferred per the S77 server.py decision. Can land any time the log noise becomes annoying. Roughly 5 lines in `server.py` (early-return the function and the scheduler tick at L2959).
7. **δ→γ week-2 decision: 16 May 2026.**

---

## Decision-of-the-session

**Recovering the failed `refresh_mac_db.sh` invocation via `launchctl start` rather than re-running the script directly.** The script is well-built and fully idempotent (mv only happens after integrity_check passes), so re-running it would have been safe. But the *invocation mechanism* was the failure mode — running it via the bridge had a known race with Flask being killed mid-script. Switching to `launchctl start` removed the bridge-survival dependency entirely.

This pattern is worth standardizing: when a shell-bridge-driven script kills Flask as part of its work, prefer running it via launchd (`launchctl start <label>`) rather than directly. Logs are already routed to a known file by the plist; the launchd-spawned process tree survives the bridge dying. Add to NOTES rules in S78 closure.
