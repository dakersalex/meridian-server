import subprocess

scp = subprocess.run(['scp', '-o', 'StrictHostKeyChecking=no',
    '/Users/alexdakers/meridian-server/tmp_vps_diag.py', 'root@204.168.179.158:/tmp/vps_fix.py'],
    capture_output=True, text=True, timeout=15)
run = subprocess.run(['ssh', '-o', 'StrictHostKeyChecking=no', 'root@204.168.179.158', 'python3 /tmp/vps_fix.py'],
    capture_output=True, text=True, timeout=20)
with open('/Users/alexdakers/meridian-server/tmp_diag.txt', 'w') as f:
    f.write(run.stdout + run.stderr)
print("DONE")
