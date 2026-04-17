import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

# Fix the insert in ai_pick_economist_weekly to extract pub_date from URL
old = (
    '                    _aid = _hh.sha1(f"The Economist:{_url}".encode()).hexdigest()[:16]\n'
    '                    with sqlite3.connect(DB_PATH) as _fx:\n'
    '                        _fx.execute(\n'
    '                            "INSERT OR IGNORE INTO articles "\n'
    '                            "(id,source,url,title,body,summary,topic,tags,saved_at,fetched_at,status,pub_date,auto_saved) "\n'
    '                            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",\n'
    '                            (_aid, "The Economist", _url, _title, "", "", "", "[]",\n'
    '                             now_ts(), now_ts(), "title_only", "", 1)\n'
    '                        )\n'
)
new = (
    '                    _aid = _hh.sha1(f"The Economist:{_url}".encode()).hexdigest()[:16]\n'
    '                    _pm = _re.search(r"/(\\d{4})/(\\d{2})/(\\d{2})/", _url)\n'
    '                    _pub = f"{_pm.group(1)}-{_pm.group(2)}-{_pm.group(3)}" if _pm else ""\n'
    '                    with sqlite3.connect(DB_PATH) as _fx:\n'
    '                        _fx.execute(\n'
    '                            "INSERT OR IGNORE INTO articles "\n'
    '                            "(id,source,url,title,body,summary,topic,tags,saved_at,fetched_at,status,pub_date,auto_saved) "\n'
    '                            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",\n'
    '                            (_aid, "The Economist", _url, _title, "", "", "", "[]",\n'
    '                             now_ts(), now_ts(), "title_only", _pub, 1)\n'
    '                        )\n'
)
assert old in content, "Insert pattern not found"
content = content.replace(old, new, 1)
print("pub_date from URL fix applied")

ast.parse(content)
print("Syntax OK")
with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
