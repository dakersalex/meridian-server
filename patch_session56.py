import ast, re

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

old = (
    '    snapshot_date = datetime.now().strftime("%Y-%m-%d")\n'
    '    added = 0\n'
    '    with sqlite3.connect(DB_PATH) as cx:\n'
    '        existing_urls = set(normalise_url(r[0]) for r in cx.execute("SELECT url FROM suggested_articles").fetchall())\n'
    '        for a in articles:\n'
    '            url = a.get("url","")\n'
    '            if not url or normalise_url(url) in existing_urls:\n'
    '                continue\n'
    '            cx.execute(\n'
    '                "INSERT INTO suggested_articles (title,url,source,snapshot_date,score,reason,added_at,status,pub_date) VALUES (?,?,?,?,?,?,?,\'new\',?)",\n'
    '                (a.get("title",""), url, a.get("source",""),\n'
    '                 snapshot_date, a.get("score",0), a.get("reason",""), now_ts(), a.get("pub_date",""))\n'
    '            )\n'
)
new = (
    '    snapshot_date = datetime.now().strftime("%Y-%m-%d")\n'
    '    _SUG_MONTHS = {"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,\n'
    '                   "july":7,"august":8,"september":9,"october":10,"november":11,"december":12}\n'
    '    def _norm_date(raw):\n'
    '        import re as _re\n'
    '        if not raw: return ""\n'
    '        raw = raw.strip()\n'
    '        if _re.match(r"\\d{4}-\\d{2}-\\d{2}", raw): return raw\n'
    '        m = _re.match(r"(\\d{1,2})\\s+([A-Za-z]+)\\s+(\\d{4})", raw)\n'
    '        if m:\n'
    '            mo = _SUG_MONTHS.get(m.group(2).lower())\n'
    '            if mo: return f"{m.group(3)}-{mo:02d}-{int(m.group(1)):02d}"\n'
    '        m = _re.match(r"([A-Za-z]+)\\s+(\\d{1,2}),?\\s+(\\d{4})", raw)\n'
    '        if m:\n'
    '            mo = _SUG_MONTHS.get(m.group(1).lower())\n'
    '            if mo: return f"{m.group(3)}-{mo:02d}-{int(m.group(2)):02d}"\n'
    '        m = _re.match(r"([A-Za-z]+)\\s+(\\d{4})$", raw)\n'
    '        if m:\n'
    '            mo = _SUG_MONTHS.get(m.group(1).lower())\n'
    '            if mo: return f"{m.group(2)}-{mo:02d}-01"\n'
    '        return raw\n'
    '    added = 0\n'
    '    with sqlite3.connect(DB_PATH) as cx:\n'
    '        existing_urls = set(normalise_url(r[0]) for r in cx.execute("SELECT url FROM suggested_articles").fetchall())\n'
    '        for a in articles:\n'
    '            url = a.get("url","")\n'
    '            if not url or normalise_url(url) in existing_urls:\n'
    '                continue\n'
    '            cx.execute(\n'
    '                "INSERT INTO suggested_articles (title,url,source,snapshot_date,score,reason,added_at,status,pub_date) VALUES (?,?,?,?,?,?,?,\'new\',?)",\n'
    '                (a.get("title",""), url, a.get("source",""),\n'
    '                 snapshot_date, a.get("score",0), a.get("reason",""), now_ts(), _norm_date(a.get("pub_date","")))\n'
    '            )\n'
)

assert old in content, "Pattern not found"
content = content.replace(old, new, 1)

ast.parse(content)
print("Syntax OK")
with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
