#!/bin/bash
#
# ============================================================================
# BLOCK 5 ROLLBACK — restore Mac write authority.
# ============================================================================
#
# Per PHASE_2_PLAN.md § 2: "Mac plist: launchctl load
# ~/Library/LaunchAgents/com.alexdakers.meridian.sync.plist → wake_sync
# resumes." (NB: the actual plist label on Alex's Mac is .wakesync, not
# .sync — the plan was drafted before the live label was confirmed.)
#
# Per § 8 P2-10 rollback: "launchctl load the plist; wake_sync resumes.
# Mac DB is a snapshot, so no data loss even if rollback delayed."
#
# Per § 2: "Rollback to Phase-1 parallel-run is a single launchctl
# command per plist." This script wraps that single command plus the
# wake_and_sync.sh restore from archive, plus a verification step.
# Designed to run in <2 minutes per § 2.
#
# Idempotent: each step checks state before mutating, so this script
# is safe to run after a partial cutover failure or as a paranoid
# re-run after a successful rollback.
#
# Steps:
#   1. Restore wake_and_sync.sh from most recent archive
#   2. launchctl load com.alexdakers.meridian.wakesync
#   3. Verify scheduler resumed (launchctl list shows label)
#   4. Smoke-call the wake script directly to confirm it's executable
#
# What this script does NOT undo:
#   - The pre-cutover Mac DB snapshot in db_backups/. That stays as
#     audit trail; harmless to keep, useful if you ever need to
#     replay state.
#   - Any VPS-side changes (cron addition, deployed
#     economist_weekly_pick.py). Those are independent of P2-10 and
#     have separate rollback paths if needed.

set -e
set -u
set -o pipefail

# ── Configuration ───────────────────────────────────────────────────────────
REPO_DIR="/Users/alexdakers/meridian-server"
ARCHIVE_DIR="${REPO_DIR}/archive"
WAKE_SCRIPT="${REPO_DIR}/wake_and_sync.sh"
PLIST_LABEL="com.alexdakers.meridian.wakesync"
PLIST_PATH="${HOME}/Library/LaunchAgents/${PLIST_LABEL}.plist"

echo "════════════════════════════════════════════════════════════════════"
echo "  BLOCK 5 ROLLBACK — restore Mac sync authority"
echo "  Started: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "════════════════════════════════════════════════════════════════════"

# ── Step 1: Restore wake_and_sync.sh ────────────────────────────────────────
echo ""
echo "── Step 1/4: Restore wake_and_sync.sh from archive ──────────────────"
if [ -f "${WAKE_SCRIPT}" ]; then
    echo "${WAKE_SCRIPT} already in place — no restore needed."
else
    if [ ! -d "${ARCHIVE_DIR}" ]; then
        echo "ERROR: archive/ directory missing. Cannot restore."
        echo "       wake_and_sync.sh is also missing. Manual recovery required."
        exit 1
    fi
    LATEST_ARCHIVE="$(ls -t "${ARCHIVE_DIR}"/wake_and_sync_*.sh 2>/dev/null | head -1 || true)"
    if [ -z "${LATEST_ARCHIVE}" ]; then
        echo "ERROR: no wake_and_sync_*.sh archive found in ${ARCHIVE_DIR}"
        echo "       Manual recovery: pull from git history with:"
        echo "         cd ${REPO_DIR} && git show HEAD:wake_and_sync.sh > wake_and_sync.sh"
        exit 1
    fi
    echo "Restoring from ${LATEST_ARCHIVE} → ${WAKE_SCRIPT}"
    cp "${LATEST_ARCHIVE}" "${WAKE_SCRIPT}"
    chmod +x "${WAKE_SCRIPT}"
    ls -la "${WAKE_SCRIPT}"
fi
echo "Step 1 done."

# ── Step 2: launchctl load wakesync ─────────────────────────────────────────
echo ""
echo "── Step 2/4: launchctl load ${PLIST_LABEL} ──────────────────────────"
if [ ! -f "${PLIST_PATH}" ]; then
    echo "ERROR: plist not found at ${PLIST_PATH}"
    exit 1
fi
if launchctl list "${PLIST_LABEL}" >/dev/null 2>&1; then
    echo "Already loaded — no-op."
else
    launchctl load "${PLIST_PATH}"
    sleep 1
    echo "Loaded."
fi
echo "Step 2 done."

# ── Step 3: Verify scheduler resumed ────────────────────────────────────────
echo ""
echo "── Step 3/4: Verify scheduler ───────────────────────────────────────"
if launchctl list "${PLIST_LABEL}" >/dev/null 2>&1; then
    echo "${PLIST_LABEL} present in launchctl list:"
    launchctl list | grep "${PLIST_LABEL}" || true
else
    echo "ERROR: ${PLIST_LABEL} NOT in launchctl list after load."
    exit 1
fi
echo "Step 3 done."

# ── Step 4: Sanity-check the wake script is executable ──────────────────────
echo ""
echo "── Step 4/4: Sanity check wake_and_sync.sh ──────────────────────────"
if [ ! -x "${WAKE_SCRIPT}" ]; then
    echo "ERROR: wake_and_sync.sh is not executable. Fixing…"
    chmod +x "${WAKE_SCRIPT}"
fi
# bash -n: parse-only check, doesn't actually execute the script.
bash -n "${WAKE_SCRIPT}"
echo "Syntax OK."
echo "Step 4 done."

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  BLOCK 5 ROLLBACK COMPLETE"
echo "  ${PLIST_LABEL}: loaded"
echo "  ${WAKE_SCRIPT}: in place, executable, syntactically valid"
echo ""
echo "  Next scheduled wake_sync run: per StartCalendarInterval in"
echo "  ${PLIST_PATH} (currently 05:40 + 11:40 Geneva)."
echo "  To force an immediate run for verification:"
echo "    bash ${WAKE_SCRIPT}"
echo "════════════════════════════════════════════════════════════════════"
