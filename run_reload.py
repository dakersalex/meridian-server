import subprocess, time, sys

r = subprocess.run(
    [sys.executable, '/Users/alexdakers/meridian-server/reload_launchd.py'],
    capture_output=True, text=True, timeout=20
)
print(r.stdout)
print(r.stderr)
