#!/usr/bin/env python3
import subprocess, time, urllib.request, sys

# Find and kill Flask on 4242
result = subprocess.run(['lsof', '-ti', 'tcp:4242'], capture_output=True, text=True)
pids = [p.strip() for p in result.stdout.strip().split('\n') if p.strip()]
print(f"Killing PIDs: {pids}")
for pid in pids:
    subprocess.run(['kill', '-9', pid])

time.sleep(3)

# Start Flask directly, detached
proc = subprocess.Popen(
    ['/Users/alexdakers/meridian-server/venv/bin/python3',
     '/Users/alexdakers/meridian-server/server.py'],
    cwd='/Users/alexdakers/meridian-server',
    stdout=open('/Users/alexdakers/meridian-server/logs/server.log', 'a'),
    stderr=subprocess.STDOUT,
    start_new_session=True
)
print(f"Started Flask PID: {proc.pid}")

# Wait and verify
for i in range(10):
    time.sleep(2)
    try:
        resp = urllib.request.urlopen('http://localhost:4242/api/health', timeout=3)
        print(f"Flask up after {(i+1)*2}s — health OK")
        # Also verify new route
        resp2 = urllib.request.urlopen('http://localhost:4242/api/images/recent?limit=1&every_nth=5', timeout=3)
        print(f"images/recent route: {resp2.status}")
        break
    except Exception as e:
        print(f"Attempt {i+1}: {e}")
else:
    print("Flask did not come up in time")
    sys.exit(1)
