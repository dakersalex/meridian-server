import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

old = ("        cx.execute('CREATE TABLE IF NOT EXISTS kt_meta '\n"
       "                   '(key TEXT PRIMARY KEY, value TEXT NOT NULL)')\n")
new = ("        cx.execute('CREATE TABLE IF NOT EXISTS kt_meta '\n"
       "                   '(key TEXT PRIMARY KEY, value TEXT NOT NULL)')\n"
       "        # Performance indexes — safe to run every startup (IF NOT EXISTS)\n"
       "        for _idx in [\n"
       "            'CREATE INDEX IF NOT EXISTS idx_art_pub_date ON articles(pub_date DESC)',\n"
       "            'CREATE INDEX IF NOT EXISTS idx_art_saved_at ON articles(saved_at DESC)',\n"
       "            'CREATE INDEX IF NOT EXISTS idx_art_source ON articles(source)',\n"
       "            'CREATE INDEX IF NOT EXISTS idx_art_status ON articles(status)',\n"
       "            'CREATE INDEX IF NOT EXISTS idx_art_auto_saved ON articles(auto_saved)',\n"
       "        ]:\n"
       "            cx.execute(_idx)\n")

assert old in content, "kt_meta not found"
content = content.replace(old, new, 1)
print("Indexes added to init_db")

ast.parse(content)
print("Syntax OK")
with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
