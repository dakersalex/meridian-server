import ast, re

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

old_cap = re.search(
    r'    # Filter to last 36h, then apply per-source caps.*?if not candidates:\n        log\.info\("AI pick: no candidates within last 36h — nothing to score"\)\n        with sqlite3\.connect\(DB_PATH\) as _rx:\n            _rx\.execute\("INSERT OR REPLACE INTO kt_meta \(key, value\) VALUES \(\?, \?\)", \(_gate_key, _today\)\)\n        return \[\], \[\]\n',
    content, re.DOTALL
)

if not old_cap:
    print("Pattern not found — trying simpler match")
    # Show what's around that area
    idx = content.find('# Filter to last 36h, then apply per-source caps')
    print(repr(content[idx:idx+800]))
else:
    new_cap = (
        '    # Filter to last 36h — no pre-scoring cap\n'
        '    # Removed per-source caps: risk of dropping high-scoring articles outweighs latency benefit\n'
        '    from datetime import datetime as _dt, timezone as _tz, timedelta as _td\n'
        '    _cutoff = (_dt.now(_tz.utc) - _td(hours=36)).strftime("%Y-%m-%d")\n'
        '    _before = len(candidates)\n'
        '    candidates = [a for a in candidates if not a.get("pub_date") or a.get("pub_date","") >= _cutoff]\n'
        '    if len(candidates) < _before:\n'
        '        log.info(f"AI pick: filtered {_before - len(candidates)} old candidates (>36h), {len(candidates)} remain")\n'
        '    if not candidates:\n'
        '        log.info("AI pick: no candidates within 36h — nothing to score")\n'
        '        with sqlite3.connect(DB_PATH) as _rx:\n'
        '            _rx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES (?, ?)", (_gate_key, _today))\n'
        '        return [], []\n'
    )
    content = content[:old_cap.start()] + new_cap + content[old_cap.end():]
    ast.parse(content)
    print("Syntax OK")
    with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
        f.write(content)
    print("Done")
