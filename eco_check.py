import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

old = ('        q = ("SELECT id,source,url,title,topic,tags,status,pub_date,saved_at,auto_saved "\n'
       '             "FROM articles {} "\n')
new = ('        q = ("SELECT id,source,url,title,summary,topic,tags,status,pub_date,saved_at,auto_saved "\n'
       '             "FROM articles {} "\n')
assert old in content, "query not found"
content = content.replace(old, new, 1)

old2 = ('"body": "", "summary": "",\n')
new2 = ('"body": "", "summary": r["summary"] or "",\n')
assert old2 in content, "summary line not found"
content = content.replace(old2, new2, 1)

ast.parse(content)
print("Syntax OK")
with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
