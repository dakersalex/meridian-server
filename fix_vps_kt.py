import subprocess

sql = """
UPDATE kt_meta SET value='2026-04-14T05:40:12' WHERE key='last_sync_economist';
UPDATE kt_meta SET value='2026-04-14T05:40:38' WHERE key='last_sync_fa';
UPDATE kt_meta SET value='2026-04-14T05:40:19' WHERE key='last_sync_ft';
"""

cmd = f'python3 -c "import sqlite3; db=sqlite3.connect(\'/opt/meridian-server/meridian.db\'); c=db.cursor(); c.execute(\'UPDATE kt_meta SET value=\\\"2026-04-14T05:40:12\\\" WHERE key=\\\"last_sync_economist\\\"\'); c.execute(\'UPDATE kt_meta SET value=\\\"2026-04-14T05:40:38\\\" WHERE key=\\\"last_sync_fa\\\"\'); c.execute(\'UPDATE kt_meta SET value=\\\"2026-04-14T05:40:19\\\" WHERE key=\\\"last_sync_ft\\\"\'); db.commit(); print(\'updated\', c.rowcount)"'

r = subprocess.run(
    ['ssh', '-o', 'StrictHostKeyChecking=no', 'root@204.168.179.158', cmd],
    capture_output=True, text=True, timeout=30
)
with open('/Users/alexdakers/meridian-server/logs/vps_kt_fix.txt', 'w') as f:
    f.write(r.stdout + r.stderr)
print(r.stdout + r.stderr)
