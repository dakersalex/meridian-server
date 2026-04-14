import subprocess, time

# Find the plist
r = subprocess.run('ls ~/Library/LaunchAgents/ | grep meridian', shell=True, capture_output=True, text=True)
print("Plist files:", r.stdout)

# Load it
r2 = subprocess.run(
    'launchctl load ~/Library/LaunchAgents/com.alexdakers.meridian.plist',
    shell=True, capture_output=True, text=True
)
print("Load:", r2.stdout, r2.stderr)

time.sleep(4)

# Check Flask is up
r3 = subprocess.run('curl -s http://localhost:4242/api/health', shell=True, capture_output=True, text=True)
print("Health:", r3.stdout)
