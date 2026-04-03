import subprocess, time

# Find the Flask PID on port 4242
result = subprocess.run(['lsof', '-ti', 'tcp:4242'], capture_output=True, text=True)
pids = result.stdout.strip().split('\n')
print(f"Flask PIDs on 4242: {pids}")

# Kill them — launchd will auto-respawn
for pid in pids:
    if pid:
        subprocess.run(['kill', pid])
        print(f"Killed PID {pid}")

time.sleep(4)

# Verify new process is up
result2 = subprocess.run(['lsof', '-ti', 'tcp:4242'], capture_output=True, text=True)
print(f"New PIDs: {result2.stdout.strip()}")

# Verify new route exists
import urllib.request
try:
    resp = urllib.request.urlopen('http://localhost:4242/api/images/recent?limit=1&every_nth=5', timeout=5)
    print("Route OK:", resp.status)
except Exception as e:
    print("Route error:", e)
