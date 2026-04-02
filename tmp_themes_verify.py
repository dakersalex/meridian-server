import subprocess, json

result = subprocess.run(
    ['ssh', '-o', 'StrictHostKeyChecking=no', 'root@204.168.179.158', '''python3 -c "
import sqlite3, json
c = sqlite3.connect('/opt/meridian-server/meridian.db')
cols = [r[1] for r in c.execute('PRAGMA table_info(kt_themes)').fetchall()]
print('COLS:', cols)
themes = c.execute('SELECT * FROM kt_themes ORDER BY rowid').fetchall()
out = []
for row in themes:
    d = dict(zip(cols, row))
    kw = json.loads(d.get('keywords','[]') or '[]')
    kf = json.loads(d.get('key_facts','[]') or '[]')
    out.append({'name': d.get('name'), 'emoji': d.get('emoji'), 'keywords': kw, 'kf_count': len(kf), 'kf_sample': kf[:2]})
print(json.dumps(out, indent=2))
"'''],
    capture_output=True, text=True, timeout=30
)
with open('/Users/alexdakers/meridian-server/tmp_themes_check.txt', 'w') as f:
    f.write(result.stdout + result.stderr)
print("DONE")
