"""Update wake_and_sync.sh image push block to include mac_id (r[0] = id column)."""
path = "/Users/alexdakers/meridian-server/wake_and_sync.sh"
with open(path, "r") as f:
    src = f.read()

# Replace the image_data line in the list comprehension to also include mac_id
OLD = "    images = [{'article_id':r[0],'caption':r[1],'description':r[2],'insight':r[3],'image_data':base64.b64encode(r[4]).decode('ascii'),'width':r[5],'height':r[6],'captured_at':r[7]} for r in rows]\n"
NEW = "    images = [{'mac_id':r[0],'article_id':r[1],'caption':r[2],'description':r[3],'insight':r[4],'image_data':base64.b64encode(r[5]).decode('ascii'),'width':r[6],'height':r[7],'captured_at':r[8]} for r in rows]\n"

# Also fix the SELECT to include id as first column
OLD_Q = "q = 'SELECT article_id,caption,description,insight,image_data,width,height,captured_at FROM article_images WHERE insight != \"\" AND insight IS NOT NULL AND image_data IS NOT NULL'\n"
NEW_Q = "q = 'SELECT id,article_id,caption,description,insight,image_data,width,height,captured_at FROM article_images WHERE insight != \"\" AND insight IS NOT NULL AND image_data IS NOT NULL'\n"

assert OLD in src, "List comprehension line not found"
assert OLD_Q in src, "Query line not found"
src = src.replace(OLD_Q, NEW_Q, 1)
src = src.replace(OLD, NEW, 1)

with open(path, "w") as f:
    f.write(src)
print("wake_and_sync.sh updated OK")
