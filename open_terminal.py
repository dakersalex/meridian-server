import subprocess

# Use osascript to open Terminal and run the Flask restart command
script = '''
tell application "Terminal"
    activate
    do script "lsof -ti tcp:4242 | xargs kill -9 2>/dev/null; sleep 2; launchctl load ~/Library/LaunchAgents/com.alexdakers.meridian.plist; echo Flask restarted"
end tell
'''

r = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
print("stdout:", r.stdout)
print("stderr:", r.stderr)
print("rc:", r.returncode)
