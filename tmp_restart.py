#!/usr/bin/env python3
"""Restart the Meridian Flask server via launchctl."""
import subprocess, time, sys

plist = '/Users/alexdakers/Library/LaunchAgents/com.alexdakers.meridian.plist'

# Unload
subprocess.run(['launchctl', 'unload', plist], capture_output=True)
time.sleep(1)

# Load
result = subprocess.run(['launchctl', 'load', plist], capture_output=True, text=True)
print('load:', result.stdout, result.stderr)
time.sleep(3)

# Verify
import urllib.request
try:
    with urllib.request.urlopen('http://localhost:4242/api/health', timeout=5) as r:
        print('Flask up:', r.read().decode())
except Exception as e:
    print('Flask not up yet:', e)
    sys.exit(1)
