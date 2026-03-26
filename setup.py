#!/usr/bin/env python3
"""
Meridian setup — run once to install dependencies and store credentials.
"""

import subprocess
import sys
import json
import os
from pathlib import Path

CREDS_FILE = Path(__file__).parent / "credentials.json"


def pip_install(*packages):
    subprocess.check_call([sys.executable, "-m", "pip", "install", *packages])


def main():
    print("\n" + "═" * 55)
    print("  Meridian · Server Setup")
    print("═" * 55 + "\n")

    print("Installing Python dependencies …")
    pip_install("flask", "flask-cors", "beautifulsoup4", "lxml")

    print("\nInstalling Playwright …")
    pip_install("playwright")
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])

    print("\n" + "─" * 55)
    print("Credentials setup")
    print("Your credentials are stored locally in credentials.json")
    print("and are never sent anywhere except to the publication login pages.")
    print("─" * 55)

    creds = {}

    for source, label in [("ft", "Financial Times"), ("economist", "The Economist"), ("bloomberg", "Bloomberg")]:
        print(f"\n{label}")
        email    = input(f"  Email: ").strip()
        password = input(f"  Password: ").strip()
        if email and password:
            creds[source] = {"email": email, "password": password}
        else:
            print(f"  Skipping {label} (no credentials entered)")

    with open(CREDS_FILE, "w") as f:
        json.dump(creds, f, indent=2)
    os.chmod(CREDS_FILE, 0o600)

    print("\n✓ Credentials saved to credentials.json (chmod 600)")
    print("\n" + "═" * 55)
    print("  Setup complete!")
    print("═" * 55)
    print("\nTo start the server:")
    print("  python server.py")
    print("\nOr to run a one-off sync:")
    print("  python sync_now.py")
    print("\nThe server will run at http://localhost:4242")
    print("Open Meridian and click 'Sync' to pull your saved articles.\n")


if __name__ == "__main__":
    main()
