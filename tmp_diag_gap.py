"""Diagnose image gap: compare Mac vs VPS article_ids."""
import sqlite3, json, urllib.request, base64

MAC_DB = "/Users/alexdakers/meridian-server/meridian.db"

# Get Mac image article_ids
conn = sqlite3.connect(MAC_DB)
mac_rows = conn.execute(
    "SELECT article_id, caption FROM article_images "
    "WHERE insight != '' AND insight IS NOT NULL AND image_data IS NOT NULL"
).fetchall()
conn.close()

mac_keys = set((r[0], r[1][:30]) for r in mac_rows)
print(f"Mac: {len(mac_rows)} images, {len(set(r[0] for r in mac_rows))} articles")

# Check VPS via SSH
import subprocess
vps_result = subprocess.run(
    ["ssh", "root@204.168.179.158",
     "python3 -c \""
     "import sqlite3; db=sqlite3.connect('/opt/meridian-server/meridian.db'); "
     "rows=db.execute('SELECT article_id, caption FROM article_images').fetchall(); "
     "print(len(rows)); "
     "[print(r[0], repr(r[1][:30])) for r in rows[:5]]"
     "\""],
    capture_output=True, text=True
)
print("VPS output:", vps_result.stdout)

# Find Mac article_ids not on VPS
vps_res2 = subprocess.run(
    ["ssh", "root@204.168.179.158",
     "python3 -c \""
     "import sqlite3,json; db=sqlite3.connect('/opt/meridian-server/meridian.db'); "
     "rows=db.execute('SELECT article_id FROM article_images').fetchall(); "
     "ids=set(r[0] for r in rows); print(json.dumps(list(ids)))"
     "\""],
    capture_output=True, text=True
)
try:
    vps_ids = set(json.loads(vps_res2.stdout.strip()))
    mac_ids = set(r[0] for r in mac_rows)
    missing = mac_ids - vps_ids
    print(f"Missing article_ids on VPS: {len(missing)}")
    for mid in list(missing)[:5]:
        caps = [r[1] for r in mac_rows if r[0] == mid]
        print(f"  {mid}: {caps}")
except Exception as e:
    print(f"Parse error: {e}, raw: {vps_res2.stdout[:200]}")
