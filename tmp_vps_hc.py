import subprocess, json

# Check VPS via SSH
cmd = """ssh -o StrictHostKeyChecking=no root@204.168.179.158 "python3 -c \\"
import sqlite3, json
c = sqlite3.connect(\\'/opt/meridian-server/meridian.db\\')
sources = dict(c.execute(\\'SELECT source, COUNT(*) FROM articles GROUP BY source\\').fetchall())
total = sum(sources.values())
tables = [r[0] for r in c.execute(\\'SELECT name FROM sqlite_master WHERE type=\\\\\\'table\\\\\\'\\').fetchall()]
kt = c.execute(\\'SELECT COUNT(*) FROM kt_themes\\').fetchone()[0] if \\'kt_themes\\' in tables else 0
tagged = c.execute(\\'SELECT COUNT(*) FROM articles WHERE theme_id IS NOT NULL\\').fetchone()[0]
kf = c.execute(\\'SELECT COUNT(*) FROM kt_themes WHERE key_facts != \\\\\\'[]\\\\\\' AND key_facts IS NOT NULL AND key_facts != \\\\\\'\\\\\\'\\').fetchone()[0] if \\'kt_themes\\' in tables else 0
imgs = c.execute(\\'SELECT COUNT(*) FROM article_images\\').fetchone()[0] if \\'article_images\\' in tables else 0
print(json.dumps({\\'total\\':total,\\'sources\\':sources,\\'kt\\':kt,\\'tagged\\':tagged,\\'kf\\':kf,\\'imgs\\':imgs}))
\\""
"""
result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
with open('/tmp/vps_hc.txt', 'w') as f:
    f.write(result.stdout + result.stderr)
print("VPS_HC_DONE")
