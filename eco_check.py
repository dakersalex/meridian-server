import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

# Fix 1: FT pub_date fallback to today in feed scrape
old1 = "pub_date: a.publishedDate ? a.publishedDate.substring(0, 10) : '',"
new1 = "pub_date: a.publishedDate ? a.publishedDate.substring(0, 10) : new Date().toISOString().substring(0, 10),"
if old1 in content:
    content = content.replace(old1, new1, 1)
    print("Fix 1 applied: FT feed pub_date fallback")
else:
    print("Fix 1 already applied or not found")

# Fix 2: FT DOM fallback pub_date to today
old2 = "results.push({{title, url, source: 'Financial Times', pub_date: '', standfirst: '', is_opinion: false, is_podcast: false, already_saved: false}});"
new2 = "results.push({{title, url, source: 'Financial Times', pub_date: new Date().toISOString().substring(0, 10), standfirst: '', is_opinion: false, is_podcast: false, already_saved: false}});"
if old2 in content:
    content = content.replace(old2, new2, 1)
    print("Fix 2 applied: FT DOM fallback pub_date")
else:
    print("Fix 2 already applied or not found")

# Fix 3: DB indexes in init_db
old3 = ("        cx.execute('CREATE TABLE IF NOT EXISTS kt_meta '\n"
        "                   '(key TEXT PRIMARY KEY, value TEXT NOT NULL)')\n")
new3 = ("        cx.execute('CREATE TABLE IF NOT EXISTS kt_meta '\n"
        "                   '(key TEXT PRIMARY KEY, value TEXT NOT NULL)')\n"
        "        for _idx in [\n"
        "            'CREATE INDEX IF NOT EXISTS idx_art_pub_date ON articles(pub_date DESC)',\n"
        "            'CREATE INDEX IF NOT EXISTS idx_art_saved_at ON articles(saved_at DESC)',\n"
        "            'CREATE INDEX IF NOT EXISTS idx_art_source ON articles(source)',\n"
        "            'CREATE INDEX IF NOT EXISTS idx_art_status ON articles(status)',\n"
        "            'CREATE INDEX IF NOT EXISTS idx_art_auto_saved ON articles(auto_saved)',\n"
        "        ]:\n"
        "            cx.execute(_idx)\n")
if old3 in content:
    content = content.replace(old3, new3, 1)
    print("Fix 3 applied: DB indexes")
else:
    print("Fix 3 not found — checking alternate location")

ast.parse(content)
print("Syntax OK")
with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
