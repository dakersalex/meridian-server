import subprocess

r = subprocess.run(
    ['ssh', '-o', 'StrictHostKeyChecking=no', 'root@204.168.179.158',
     'python3 -c "import sqlite3; db=sqlite3.connect(\'/opt/meridian-server/meridian.db\'); c=db.cursor(); c.execute(\'SELECT key, value FROM kt_meta WHERE key LIKE \\\"last_sync%\\\"\'); [print(row) for row in c.fetchall()]"'],
    capture_output=True, text=True, timeout=30
)
with open('/Users/alexdakers/meridian-server/logs/vps_kt_check.txt', 'w') as f:
    f.write(r.stdout + r.stderr)
print(r.stdout + r.stderr)
