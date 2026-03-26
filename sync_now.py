#!/usr/bin/env python3
"""
meridian sync_now.py — trigger a one-off sync without starting the full server.
Usage:
  python sync_now.py              # sync all sources
  python sync_now.py ft           # sync FT only
  python sync_now.py economist    # sync Economist only
  python sync_now.py bloomberg    # sync Bloomberg only
"""

import sys
import json
from pathlib import Path

# make server module importable
sys.path.insert(0, str(Path(__file__).parent))

from server import (
    init_db, run_sync, SCRAPERS, load_creds, log
)


def main():
    init_db()
    creds = load_creds()

    if not creds:
        print("No credentials found. Run `python setup.py` first.")
        sys.exit(1)

    sources = sys.argv[1:] if len(sys.argv) > 1 else list(SCRAPERS.keys())

    for source in sources:
        if source not in SCRAPERS:
            print(f"Unknown source: {source}. Valid: {', '.join(SCRAPERS.keys())}")
            continue
        if source not in creds:
            print(f"No credentials for {source}, skipping.")
            continue
        print(f"\nSyncing {source} …")
        run_sync(source)

    print("\nSync complete.")


if __name__ == "__main__":
    main()
