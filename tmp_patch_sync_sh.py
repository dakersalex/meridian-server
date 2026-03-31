"""Patch wake_and_sync.sh: add image push block after article push."""
path = "/Users/alexdakers/meridian-server/wake_and_sync.sh"
with open(path, "r") as f:
    src = f.read()

# Build the block as a plain string with explicit \n — no indented SQL
block = "\n"
block += "# Push article_images (Economist charts) from Mac DB to VPS\n"
block += "echo \"$(date): Pushing images to VPS\" >> \"$LOG\"\n"
block += "python3 - << 'IMGEOF' >> \"$LOG\" 2>&1\n"
block += "import sqlite3, json, urllib.request, base64\n"
block += "DB = '/Users/alexdakers/meridian-server/meridian.db'\n"
block += "VPS = 'https://meridianreader.com/api/push-images'\n"
block += "conn = sqlite3.connect(DB)\n"
block += "q = 'SELECT article_id,caption,description,insight,image_data,width,height,captured_at FROM article_images WHERE insight != \"\" AND insight IS NOT NULL AND image_data IS NOT NULL'\n"
block += "rows = conn.execute(q).fetchall()\n"
block += "conn.close()\n"
block += "if not rows:\n"
block += "    print('push-images: no images to push')\n"
block += "else:\n"
block += "    images = [{'article_id':r[0],'caption':r[1],'description':r[2],'insight':r[3],'image_data':base64.b64encode(r[4]).decode('ascii'),'width':r[5],'height':r[6],'captured_at':r[7]} for r in rows]\n"
block += "    total_upserted = 0\n"
block += "    for i in range(0, len(images), 20):\n"
block += "        batch = images[i:i+20]\n"
block += "        payload = json.dumps({'images': batch}).encode()\n"
block += "        req = urllib.request.Request(VPS, data=payload, headers={'Content-Type':'application/json'}, method='POST')\n"
block += "        try:\n"
block += "            with urllib.request.urlopen(req, timeout=60) as resp:\n"
block += "                result = json.loads(resp.read())\n"
block += "                total_upserted += result.get('upserted', 0)\n"
block += "        except Exception as e:\n"
block += "            print(f'push-images batch error: {e}')\n"
block += "            break\n"
block += "    print(f'push-images: {total_upserted} upserted of {len(images)} total')\n"
block += "IMGEOF\n"
block += "\n"

marker = 'echo "$(date): Wake sync complete" >> "$LOG"'
assert marker in src, "Marker not found"
src = src.replace(marker, block + marker, 1)

with open(path, "w") as f:
    f.write(src)

print("wake_and_sync.sh patched OK")
