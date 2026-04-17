import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

old_order = (
    '            f"SELECT * FROM suggested_articles {where} ORDER BY score DESC, added_at DESC",'
)
new_order = (
    '            f"SELECT * FROM suggested_articles {where} ORDER BY " + ("pub_date DESC, added_at DESC" if request.args.get("sort") == "date" else "score DESC, added_at DESC"),'
)
assert old_order in content, "Order pattern not found"
content = content.replace(old_order, new_order, 1)
print("Server sort patch applied")

ast.parse(content)
print("Syntax OK")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
