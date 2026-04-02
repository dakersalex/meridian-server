import subprocess
r = subprocess.run(
    ['ssh', '-o', 'StrictHostKeyChecking=no', 'root@204.168.179.158',
     'systemctl status meridian --no-pager && echo "---" && tail -20 /opt/meridian-server/meridian.log'],
    capture_output=True, text=True, timeout=20
)
with open('/Users/alexdakers/meridian-server/tmp_vps_status.txt', 'w') as f:
    f.write(r.stdout + r.stderr)
print("DONE")
