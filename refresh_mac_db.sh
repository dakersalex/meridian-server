#!/bin/bash
#
# refresh_mac_db.sh
#
# Per PHASE_2_PLAN.md § 3: "On-demand refresh. refresh_mac_db.sh remains
# as a manual override — same snapshot + scp + chmod, callable by hand
# when mid-day freshness is wanted. Compatible with the nightly job."
#
# Mechanism:
#   1. SSH to VPS, run sqlite3 source.db ".backup tmp.db" (NOT cp — avoids
#      grabbing DB mid-write).
#   2. scp the temp snapshot back to Mac.
#   3. PRAGMA integrity_check the local copy before swapping.
#   4. Stop Mac Flask, replace meridian.db, chmod 444, restart Flask.
#
# Per § 3: "Mac Flask should tolerate the file replacement; if it doesn't
# cleanly, wrap the swap in a stop/replace/start in the launchd job."
# This script does the stop/replace/start unconditionally — safer than
# trusting Flask to re-open a swapped-out SQLite handle.
#
# Usage:
#   ./refresh_mac_db.sh           # interactive run
#
# Idempotent: each run produces a fresh snapshot and atomic swap. Failed
# runs leave the previous DB in place (mv only happens after integrity_check
# passes).

set -e
set -u
set -o pipefail

# ── Configuration ───────────────────────────────────────────────────────────
VPS_HOST="root@204.168.179.158"
VPS_DB="/opt/meridian-server/meridian.db"
VPS_TMP="/tmp/meridian_snapshot_$$.db"
MAC_REPO="/Users/alexdakers/meridian-server"
MAC_DB="${MAC_REPO}/meridian.db"
MAC_TMP="${MAC_REPO}/meridian.db.refresh.$$"
FLASK_LABEL="com.alexdakers.meridian.flask"
FLASK_PLIST="${HOME}/Library/LaunchAgents/${FLASK_LABEL}.plist"

echo "════════════════════════════════════════════════════════════════════"
echo "  refresh_mac_db.sh"
echo "  Started: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "════════════════════════════════════════════════════════════════════"

# ── Step 1: Create snapshot on VPS ──────────────────────────────────────────
echo ""
echo "── Step 1/5: Snapshot VPS DB via .backup ────────────────────────────"
ssh -o StrictHostKeyChecking=no "${VPS_HOST}" \
    "sqlite3 '${VPS_DB}' \".backup '${VPS_TMP}'\" && ls -la '${VPS_TMP}'"
echo "Step 1 done."

# ── Step 2: Pull snapshot to Mac ────────────────────────────────────────────
echo ""
echo "── Step 2/5: scp snapshot Mac←VPS ───────────────────────────────────"
scp "${VPS_HOST}:${VPS_TMP}" "${MAC_TMP}"
ls -la "${MAC_TMP}"
# Clean up VPS-side temp regardless of subsequent success
ssh -o StrictHostKeyChecking=no "${VPS_HOST}" "rm -f '${VPS_TMP}'"
echo "Step 2 done."

# ── Step 3: Integrity check ─────────────────────────────────────────────────
echo ""
echo "── Step 3/5: PRAGMA integrity_check ─────────────────────────────────"
INTEGRITY="$(sqlite3 "${MAC_TMP}" 'PRAGMA integrity_check;')"
echo "Result: ${INTEGRITY}"
if [ "${INTEGRITY}" != "ok" ]; then
    echo "ERROR: integrity_check failed — leaving original Mac DB untouched"
    rm -f "${MAC_TMP}"
    exit 1
fi
echo "Step 3 done."

# ── Step 4: Stop Flask, swap DB, set read-only, restart Flask ───────────────
echo ""
echo "── Step 4/5: Stop Flask, swap DB, restart ───────────────────────────"
echo "Unloading ${FLASK_LABEL}…"
launchctl unload "${FLASK_PLIST}" 2>&1 || echo "  (already unloaded — continuing)"
sleep 2

# Belt-and-braces: the launchd plist may KeepAlive=true. Kill any orphan
# python3 process bound to port 4242 before swapping. Suppress errors —
# we only care that the port is free.
PORT_PID="$(lsof -t -i :4242 2>/dev/null || true)"
if [ -n "${PORT_PID}" ]; then
    echo "  Found orphan PID ${PORT_PID} on :4242 — killing"
    kill "${PORT_PID}" 2>/dev/null || true
    sleep 1
fi

echo "Swapping ${MAC_DB} ← ${MAC_TMP}"
# Make writable first in case it's already chmod 444 from a prior refresh.
chmod 644 "${MAC_DB}" 2>/dev/null || true
mv -f "${MAC_TMP}" "${MAC_DB}"
chmod 444 "${MAC_DB}"
ls -la "${MAC_DB}"

echo "Loading ${FLASK_LABEL}…"
launchctl load "${FLASK_PLIST}"
sleep 2
if launchctl list "${FLASK_LABEL}" >/dev/null 2>&1; then
    echo "  Flask agent loaded."
else
    echo "ERROR: Flask agent did not load. Manual intervention needed."
    exit 1
fi
echo "Step 4 done."

# ── Step 5: Smoke check Flask ───────────────────────────────────────────────
echo ""
echo "── Step 5/5: Flask smoke check on :4242 ─────────────────────────────"
sleep 2
HTTP_CODE="$(curl -s -o /tmp/refresh_smoke.json -w '%{http_code}' http://127.0.0.1:4242/api/health/daily || echo '000')"
echo "HTTP status: ${HTTP_CODE}"
if [ "${HTTP_CODE}" != "200" ]; then
    echo "WARNING: Flask did not return 200 on first check. May still be"
    echo "         starting up. Re-check manually with:"
    echo "         curl -i http://127.0.0.1:4242/api/health/daily"
fi
echo "Step 5 done."

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  refresh_mac_db.sh COMPLETE"
echo "  Mac DB now mirrors VPS as of: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "  Permissions: $(stat -f '%Sp' "${MAC_DB}")  (444 = read-only mirror)"
echo "════════════════════════════════════════════════════════════════════"
