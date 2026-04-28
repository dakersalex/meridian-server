#!/usr/bin/env python3
"""
Meridian — Extension write-failure watchdog (P2-8).

PHASE_2_PLAN § 6 condition 3:
> Chrome extension prod write fails at a rate > 10% over a rolling 24h window.

DESIGN NOTE — failure-rate denominator (S71):
The plan asks for a *rate*, which requires a denominator (failures + successes).
Instrumenting every successful write would either (a) double extension HTTP
traffic during 6h auto-sync bursts (client-side success logging) or
(b) require server-side hooks on every write endpoint (invasive). The proxy
candidates available cheaply (extension-origin id prefixes in `articles`,
sync_log rows, etc.) all under-count: most extension traffic is
PATCH-on-existing from the body-fetcher, which mutates rows rather than
inserting them.

S71 decision: alert on **absolute failure count** in the rolling 24h window.
A working extension produces 0 failures in a day; ≥5 failures means something
is structurally wrong (auth, CORS, VPS down, schema drift) and warrants
Alex's attention regardless of denominator. This is the operationally useful
form of condition 3, more legible than a rate. Threshold tunable; revisit
if it produces false positives in practice.

Reads the `extension_write_failures` table (populated by /api/extension/write-failure).
Fires Tier-3 alert via alert.send_alert() on threshold breach.
Writes a heartbeat line to /var/log/meridian/extension_failure_watchdog.last_run
on every successful run.

Cron: hourly. Cheap query, idempotent (same input -> same alert).
Suggested: `0 * * * *  /opt/meridian-server/venv/bin/python3 /opt/meridian-server/extension_failure_watchdog.py >> /var/log/meridian/extension_failure_watchdog.cron.log 2>&1`

Designed to run on VPS (where alert.py and the secrets file live).
"""
import os
import sys
import sqlite3
import time
import logging
from pathlib import Path

# alert.py lives next to this script on VPS (/opt/meridian-server/).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DB_PATH = Path(__file__).parent / "meridian.db"
LOG_DIR = Path("/var/log/meridian")
HEARTBEAT_FILE = LOG_DIR / "extension_failure_watchdog.last_run"
WINDOW_MS = 24 * 60 * 60 * 1000
THRESHOLD_ABS_FAILURES = 5    # alert when failures_24h >= this

# Set up logging.
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "extension_failure_watchdog.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stderr)],
)
log = logging.getLogger("ext_failure_watchdog")


def query_window(cx, now_ms):
    """Return (failures_count, sample_failures, action_breakdown)."""
    cutoff = now_ms - WINDOW_MS

    failures = cx.execute(
        "SELECT COUNT(*) FROM extension_write_failures WHERE timestamp >= ?",
        (cutoff,),
    ).fetchone()[0]

    sample = cx.execute(
        "SELECT timestamp, action, status_code, error_msg, url "
        "FROM extension_write_failures "
        "WHERE timestamp >= ? "
        "ORDER BY timestamp DESC LIMIT 5",
        (cutoff,),
    ).fetchall()

    breakdown = cx.execute(
        "SELECT action, COUNT(*) FROM extension_write_failures "
        "WHERE timestamp >= ? GROUP BY action ORDER BY COUNT(*) DESC",
        (cutoff,),
    ).fetchall()

    return failures, sample, breakdown


def write_heartbeat(now_ms):
    try:
        HEARTBEAT_FILE.write_text(str(now_ms))
    except Exception as e:
        log.warning(f"heartbeat write failed: {e}")


def main():
    if not DB_PATH.exists():
        log.error(f"DB not found at {DB_PATH}")
        return 2

    now_ms = int(time.time() * 1000)

    with sqlite3.connect(DB_PATH) as cx:
        failures, sample, breakdown = query_window(cx, now_ms)

    log.info(
        f"24h window: failures={failures} threshold={THRESHOLD_ABS_FAILURES} "
        f"breakdown={breakdown}"
    )
    write_heartbeat(now_ms)

    if failures < THRESHOLD_ABS_FAILURES:
        return 0

    # Threshold breached.
    body_lines = [
        f"Extension write failures crossed threshold.",
        f"",
        f"Window: rolling 24h",
        f"Failures: {failures}  (threshold {THRESHOLD_ABS_FAILURES})",
        f"",
        f"Action breakdown:",
    ]
    for action, count in breakdown:
        body_lines.append(f"  {action or '(empty)'}: {count}")
    body_lines += ["", "Recent failures (newest first):"]
    for ts, action, status_code, err, url in sample:
        ts_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts / 1000))
        sc = status_code if status_code is not None else "-"
        body_lines.append(
            f"  [{ts_iso}] action={action} status={sc} "
            f"err={err[:160] if err else ''} url={url[:120] if url else ''}"
        )
    body_lines += [
        "",
        "Inspect: sqlite3 /opt/meridian-server/meridian.db "
        "\"SELECT timestamp, action, status_code, error_msg, url FROM extension_write_failures "
        "ORDER BY timestamp DESC LIMIT 20;\"",
    ]
    body = "\n".join(body_lines)

    try:
        from alert import send_alert
        send_alert(
            f"extension write failures: {failures} in 24h",
            body,
            severity="tier3",
        )
        log.info("Tier-3 alert sent")
    except Exception as e:
        log.error(f"alert send failed: {e}")
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
