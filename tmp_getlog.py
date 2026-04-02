import subprocess, sys
result = subprocess.run(
    ['ssh', '-o', 'StrictHostKeyChecking=no', 'root@204.168.179.158',
     'tail -50 /opt/meridian-server/meridian.log'],
    capture_output=True, text=True, timeout=30
)
with open('/tmp/vps_log.txt', 'w') as f:
    f.write(result.stdout + result.stderr)
print("DONE")
