#!/usr/bin/env python3
"""Kill stale Flask on 4242, let launchd respawn with new code."""
import subprocess, time, urllib.request

# Kill everything on 4242
r = subprocess.run(['lsof', '-ti', 'tcp:4242'], capture_output=True, text=True)
pids = [p.strip() for p in r.stdout.strip().split('\n') if p.strip()]
print(f"Killing PIDs: {pids}")
for pid in pids:
    subprocess.run(['kill', '-9', pid])

# launchd has KeepAlive=true, will respawn automatically
print("Waiting for launchd to respawn Flask...")
for i in range(15):
    time.sleep(2)
    try:
        urllib.request.urlopen('http://localhost:4242/api/health', timeout=2)
        print(f"Flask up after {(i+1)*2}s")
        # Now test the route
        resp = urllib.request.urlopen('http://localhost:4242/api/images/recent?limit=1&every_nth=5', timeout=3)
        print(f"images/recent: HTTP {resp.status} OK")
        break
    except urllib.error.HTTPError as e:
        print(f"Attempt {i+1}: HTTP {e.code}")
        break
    except Exception as e:
        print(f"Attempt {i+1}: {e}")
else:
    print("Flask did not come up — check logs/server-error.log")
