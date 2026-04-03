#!/usr/bin/env python3
import subprocess, time, urllib.request, sys

# Find correct python
for py in ['/usr/local/bin/python3', '/usr/bin/python3', '/opt/homebrew/bin/python3']:
    r = subprocess.run([py, '--version'], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"Found python: {py} — {r.stdout.strip()}")
        PYTHON = py
        break
else:
    # fallback: check what's running flask currently / what launchd uses
    r = subprocess.run(['which', 'python3'], capture_output=True, text=True)
    PYTHON = r.stdout.strip()
    print(f"Using which python3: {PYTHON}")

# Check launchd plist for python path
import plistlib
with open('/Users/alexdakers/Library/LaunchAgents/com.alexdakers.meridian.plist', 'rb') as f:
    plist = plistlib.load(f)
print(f"Plist ProgramArguments: {plist.get('ProgramArguments')}")
print(f"Plist WorkingDirectory: {plist.get('WorkingDirectory')}")
