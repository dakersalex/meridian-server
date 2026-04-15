import subprocess
r = subprocess.run(
    ['ssh', 'root@204.168.179.158',
     "python3 -c \"import sqlite3; db=sqlite3.connect('/opt/meridian-server/meridian.db'); c=db.cursor(); c.execute(\\\"DELETE FROM articles WHERE title='Recent Books' AND source='Foreign Affairs'\\\"); db.commit(); print('deleted', c.rowcount)\""],
    capture_output=True, text=True, timeout=15
)
print(r.stdout + r.stderr)
