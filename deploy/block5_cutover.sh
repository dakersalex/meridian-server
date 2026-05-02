#!/bin/bash
#
# ============================================================================
# BLOCK 5 CUTOVER — Tier 1, atomic.
# Run ONLY after P2-9 cron is installed on VPS and verified.
# ============================================================================
#
# Per PHASE_2_PLAN.md § 8 Block 5: this script lands P2-10 (Mac write
# authority dropped) atomically. By the time you run this, P2-9 must
# already be live: economist_weekly_pick.py deployed to VPS,
# block5_cron_addition.txt appended to root crontab, one --dry-run
# verified, OR one real Thursday run completed cleanly. Otherwise
# Block 5's commit is half-landed and the rollback path is incoherent.
#
# What this script does (in order):
#   1. Snapshot Mac DB via SQLite backup API → db_backups/meridian_pre_block5_*.db
#   2. PRAGMA integrity_check on the snapshot — abort on failure
#   3. launchctl unload com.alexdakers.meridian.wakesync (the Mac sync agent)
#   4. Move wake_and_sync.sh → archive/wake_and_sync_<date>.sh
#   5. Verify VPS still healthy via /api/health/daily — abort on non-200
#
# What this script does NOT do (deliberately):
#   - Disable ai_pick_economist_weekly() in server.py. That function
#     and its Mac-Playwright dependency (eco_weekly_sub.py) live in
#     the running Mac Flask process. With the wakesync agent unloaded,
#     no scheduled call path exists; the function only fires via the
#     internal threading.Timer in server.py:2959. Until server.py is
#     edited (out of scope for S76 — hard rule), the function remains
#     callable. See BLOCK5_READY.md for the open decision.
#   - Touch the VPS or its crontab. P2-9 cron addition happens BEFORE
#     this script runs, manually.
#   - Refresh Mac DB from VPS. That's a separate concern — once Mac
#     write authority is dropped, refresh_mac_db.sh becomes the path
#     for keeping Mac Flask serving fresh data. Run it once after this
#     script completes successfully if you want immediate refresh.
#
# Failure handling: each step echoes BEFORE and AFTER. set -e is on, so
# any non-zero exit aborts the script with the next steps unrun. To
# recover from a partial run, use deploy/block5_rollback.sh — it's
# idempotent, so you can safely run it after any failure point.

set -e
set -u
set -o pipefail

# ── Configuration ───────────────────────────────────────────────────────────
REPO_DIR="/Users/alexdakers/meridian-server"
DB_PATH="${REPO_DIR}/meridian.db"
BACKUP_DIR="${REPO_DIR}/db_backups"
ARCHIVE_DIR="${REPO_DIR}/archive"
WAKE_SCRIPT="${REPO_DIR}/wake_and_sync.sh"
PLIST_LABEL="com.alexdakers.meridian.wakesync"
PLIST_PATH="${HOME}/Library/LaunchAgents/${PLIST_LABEL}.plist"
HEALTH_URL="https://meridianreader.com/api/health/daily"
TIMESTAMP="$(date +%Y%m%d_%H%M)"
TIMESTAMP_DAY="$(date +%Y%m%d)"

echo "════════════════════════════════════════════════════════════════════"
echo "  BLOCK 5 CUTOVER — atomic Mac→VPS authority transfer"
echo "  Started: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "  Hostname: $(hostname)"
echo "════════════════════════════════════════════════════════════════════"

# ── Pre-flight ──────────────────────────────────────────────────────────────
echo ""
echo "── Pre-flight ──────────────────────────────────────────────────────"
if [ ! -f "${DB_PATH}" ]; then
    echo "ERROR: Mac DB not found at ${DB_PATH}"
    exit 1
fi
if [ ! -f "${PLIST_PATH}" ]; then
    echo "ERROR: launchd plist not found at ${PLIST_PATH}"
    exit 1
fi
if [ ! -f "${WAKE_SCRIPT}" ]; then
    echo "WARNING: ${WAKE_SCRIPT} already missing — assuming partial prior run."
    echo "         Continuing; step 4 will be a no-op."
fi
mkdir -p "${BACKUP_DIR}"
mkdir -p "${ARCHIVE_DIR}"
echo "Pre-flight OK."

# ── Step 1: Snapshot Mac DB via SQLite backup API ───────────────────────────
echo ""
echo "── Step 1/5: Mac DB snapshot via .backup ────────────────────────────"
SNAPSHOT_PATH="${BACKUP_DIR}/meridian_pre_block5_${TIMESTAMP}.db"
if [ -f "${SNAPSHOT_PATH}" ]; then
    echo "ERROR: snapshot already exists at ${SNAPSHOT_PATH} — refuse to overwrite"
    exit 1
fi
echo "Snapshotting ${DB_PATH} → ${SNAPSHOT_PATH}"
sqlite3 "${DB_PATH}" ".backup '${SNAPSHOT_PATH}'"
ls -la "${SNAPSHOT_PATH}"
echo "Step 1 done."

# ── Step 2: Integrity check ─────────────────────────────────────────────────
echo ""
echo "── Step 2/5: PRAGMA integrity_check on snapshot ─────────────────────"
INTEGRITY="$(sqlite3 "${SNAPSHOT_PATH}" 'PRAGMA integrity_check;')"
echo "Result: ${INTEGRITY}"
if [ "${INTEGRITY}" != "ok" ]; then
    echo "ERROR: snapshot failed integrity check — ABORT before any state change"
    echo "       Snapshot left in place for forensics: ${SNAPSHOT_PATH}"
    exit 1
fi
echo "Step 2 done."

# ── Step 3: launchctl unload wakesync ───────────────────────────────────────
echo ""
echo "── Step 3/5: launchctl unload ${PLIST_LABEL} ────────────────────────"
# Idempotency: 'launchctl list <label>' returns exit 0 when loaded, non-zero when not.
if launchctl list "${PLIST_LABEL}" >/dev/null 2>&1; then
    echo "Currently loaded; unloading."
    launchctl unload "${PLIST_PATH}"
    sleep 1
    if launchctl list "${PLIST_LABEL}" >/dev/null 2>&1; then
        echo "ERROR: still loaded after unload — investigate"
        exit 1
    fi
    echo "Confirmed unloaded."
else
    echo "Already unloaded — no-op."
fi
echo "Step 3 done."

# ── Step 4: Archive wake_and_sync.sh ────────────────────────────────────────
echo ""
echo "── Step 4/5: Archive wake_and_sync.sh ───────────────────────────────"
if [ -f "${WAKE_SCRIPT}" ]; then
    ARCHIVE_PATH="${ARCHIVE_DIR}/wake_and_sync_${TIMESTAMP_DAY}.sh"
    if [ -f "${ARCHIVE_PATH}" ]; then
        # Already an archive from today. Add HHMM suffix to disambiguate.
        ARCHIVE_PATH="${ARCHIVE_DIR}/wake_and_sync_${TIMESTAMP}.sh"
    fi
    echo "Moving ${WAKE_SCRIPT} → ${ARCHIVE_PATH}"
    mv "${WAKE_SCRIPT}" "${ARCHIVE_PATH}"
    ls -la "${ARCHIVE_PATH}"
    echo "Confirmed: original location empty:"
    ls "${WAKE_SCRIPT}" 2>&1 | head -3 || true
else
    echo "${WAKE_SCRIPT} already absent — no-op (presumed prior partial run)."
fi
echo "Step 4 done."

# ── Step 5: VPS health verify ───────────────────────────────────────────────
echo ""
echo "── Step 5/5: VPS health verification ────────────────────────────────"
HTTP_CODE="$(curl -s -o /tmp/block5_health.json -w '%{http_code}' "${HEALTH_URL}" || echo '000')"
echo "HTTP status: ${HTTP_CODE}"
if [ "${HTTP_CODE}" != "200" ]; then
    echo "ERROR: VPS health endpoint did not return 200."
    echo "       Mac sync is now unloaded and wake script archived."
    echo "       VPS may also be down — RUN block5_rollback.sh IMMEDIATELY."
    exit 1
fi
# Light sanity: confirm 'ok' key exists and either true OR ok=false-with-info-only.
if ! grep -q '"ok"' /tmp/block5_health.json; then
    echo "ERROR: health JSON missing 'ok' key. Body:"
    cat /tmp/block5_health.json
    exit 1
fi
echo "VPS health endpoint reachable. Body summary:"
python3 -c "import json; d=json.load(open('/tmp/block5_health.json')); print({k:d.get(k) for k in ['ok','ingested_24h','last_rss_pick','title_only_pending','unenriched']})"
echo "Step 5 done."

# ── Done ────────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  BLOCK 5 CUTOVER COMPLETE"
echo "  Mac sync: unloaded"
echo "  wake_and_sync.sh: archived"
echo "  Pre-cutover snapshot: ${SNAPSHOT_PATH}"
echo "  VPS: healthy"
echo ""
echo "  NEXT: run refresh_mac_db.sh once if you want Mac Flask to"
echo "  immediately serve a fresh snapshot from VPS. Otherwise the"
echo "  nightly Mac launchd job (com.alexdakers.meridian.refresh,"
echo "  04:00 Geneva) will refresh it automatically."
echo "════════════════════════════════════════════════════════════════════"
