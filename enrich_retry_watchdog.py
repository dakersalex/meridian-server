#!/usr/bin/env python3
"""
Meridian — enrich_retry watchdog.

Phase 2 / P2-5 condition 2 (PHASE_2_PLAN § 6): alert if the nightly retry
job has not run for > 36h. Reads the heartbeat file written by
enrich_retry.py and fires a Tier-3 alert if it's stale or missing.

Designed to run from cron at 14:30 UTC daily. Idempotent — fires repeatedly
while the condition holds, which is the desired behaviour for an outage.

Exit codes:
    0 — heartbeat fresh OR alert sent successfully
    1 — alert send failed (so cron logs surface the problem)
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE_DIR = Path(__file__).resolve().parent
HEARTBEAT_FILE = Path("/var/log/meridian/enrich_retry.last_run")
LOG_FILE = Path("/var/log/meridian/enrich_retry_watchdog.log")
THRESHOLD_HOURS = 36

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def _setup_logging():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(str(LOG_FILE)), logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("enrich_retry_watchdog")


def main():
    log = _setup_logging()
    now = datetime.now(timezone.utc)

    if not HEARTBEAT_FILE.exists():
        msg = (
            f"enrich_retry has never written a heartbeat at {HEARTBEAT_FILE}.\n"
            f"Either the job has never run, or the heartbeat path is wrong.\n"
            f"Check: cron entry '30 2 * * * /opt/meridian-server/enrich_retry.py' and "
            f"/var/log/meridian/enrich_retry.log"
        )
        log.warning(msg.replace("\n", " | "))
        try:
            from alert import send_alert
            send_alert("enrich_retry has never run", msg, severity="tier3")
            log.info("alert sent (missing heartbeat)")
            return 0
        except Exception as e:
            log.error(f"alert send failed: {e}")
            return 1

    try:
        ts_text = HEARTBEAT_FILE.read_text().strip()
        last_run = datetime.fromisoformat(ts_text)
    except Exception as e:
        log.error(f"could not parse heartbeat ({HEARTBEAT_FILE}): {e}")
        try:
            from alert import send_alert
            send_alert(
                "enrich_retry heartbeat unreadable",
                f"Could not parse {HEARTBEAT_FILE}: {e}\n\nContents:\n{HEARTBEAT_FILE.read_text()[:500]}",
                severity="tier3",
            )
            return 0
        except Exception as e2:
            log.error(f"alert send failed: {e2}")
            return 1

    age = now - last_run
    log.info(f"heartbeat age: {age} (threshold {THRESHOLD_HOURS}h)")

    if age > timedelta(hours=THRESHOLD_HOURS):
        msg = (
            f"enrich_retry last ran {age} ago (at {last_run.isoformat()}).\n"
            f"Threshold is {THRESHOLD_HOURS}h. The nightly cron at 02:30 UTC "
            f"has either failed silently or stopped firing.\n\n"
            f"Investigate: /var/log/meridian/enrich_retry.log and `crontab -l`."
        )
        log.warning("threshold exceeded — firing alert")
        try:
            from alert import send_alert
            send_alert(
                f"enrich_retry stale ({int(age.total_seconds()/3600)}h since last run)",
                msg,
                severity="tier3",
            )
            log.info("alert sent (stale heartbeat)")
            return 0
        except Exception as e:
            log.error(f"alert send failed: {e}")
            return 1

    log.info("heartbeat fresh — no alert")
    return 0


if __name__ == "__main__":
    sys.exit(main())
