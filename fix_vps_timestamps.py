import subprocess, json

result = subprocess.run(
    ['curl', '-s', '-X', 'POST',
     '-H', 'Content-Type: application/json',
     '-d', '{}',
     'http://localhost:4242/api/push-articles'],
    capture_output=True, text=True, timeout=300
)

with open('/Users/alexdakers/meridian-server/logs/vps_sync_result.txt', 'w') as f:
    f.write(result.stdout)
    f.write(result.stderr)

print("done:", result.stdout[:200])
