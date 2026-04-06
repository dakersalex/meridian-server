#!/usr/bin/env python3
"""
Meridian overnight sync script.
Runs continuously, triggering a sync once per day during off-peak hours.
Quiet hours: 1am–6am. Randomised trigger time to avoid patterns.
"""

import time
import random
import datetime
import requests
import logging
import os

LOG_PATH = os.path.expanduser("~/meridian-server/logs/sync.log")
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

QUIET_START = 1   # 1am
QUIET_END   = 6   # 6am
API_BASE    = "http://localhost:4242"

def is_quiet_hours():
    hour = datetime.datetime.now().hour
    return QUIET_START <= hour < QUIET_END

def next_sync_delay():
    """Return seconds until a randomised sync time later today (or tomorrow)."""
    now = datetime.datetime.now()
    # Pick a random hour between 6am and midnight (avoiding quiet hours)
    target_hour   = random.randint(QUIET_END, 23)
    target_minute = random.randint(0, 59)
    target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    if target <= now:
        target += datetime.timedelta(days=1)
    delay = (target - now).total_seconds()
    logging.info(f"Next sync scheduled for {target.strftime('%Y-%m-%d %H:%M')}")
    return delay

def run_sync():
    if is_quiet_hours():
        logging.info("Skipping sync — quiet hours active")
        return
    try:
        logging.info("Starting sync...")
        r = requests.post(f"{API_BASE}/api/sync", json={}, timeout=120)
        r.raise_for_status()
        data = r.json()
        logging.info(f"Sync complete: {data}")
        # Enrich any title-only articles — including agent-saved ones from VPS
        logging.info("Enriching title-only articles...")
        r2 = requests.post(f"{API_BASE}/api/enrich-title-only", timeout=300)
        r2.raise_for_status()
        logging.info(f"Enrichment complete: {r2.json()}")
    except Exception as e:
        logging.error(f"Sync failed: {e}")

if __name__ == "__main__":
    logging.info("meridian_sync.py started")
    while True:
        delay = next_sync_delay()
        time.sleep(delay)
        run_sync()
