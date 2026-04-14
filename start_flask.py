#!/usr/bin/env python3
"""Spawns Flask server as a detached process."""
import subprocess, os, sys, time

# Kill any existing instance
subprocess.run('lsof -ti tcp:4242 | xargs kill -9 2>/dev/null', shell=True)
time.sleep(2)

# Start Flask
log = open('/Users/alexdakers/meridian-server/meridian.log', 'a')
proc = subprocess.Popen(
    [sys.executable, '/Users/alexdakers/meridian-server/server.py'],
    stdout=log, stderr=log,
    cwd='/Users/alexdakers/meridian-server',
    start_new_session=True
)

time.sleep(3)
# Verify
r = subprocess.run('curl -s http://localhost:4242/api/health', shell=True, capture_output=True, text=True)
print(f"PID={proc.pid} health={r.stdout.strip()}")
