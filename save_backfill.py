import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

old_cap = (
    '    # Filter to articles published in last 36h, sort newest-first, cap at 50\n'
    '    from datetime import datetime as _dt, timezone as _tz, timedelta as _td\n'
    '    _cutoff = (_dt.now(_tz.utc) - _td(hours=36)).strftime("%Y-%m-%d")\n'
    '    _before = len(candidates)\n'
    '    candidates = [a for a in candidates if not a.get("pub_date") or a.get("pub_date","") >= _cutoff]\n'
    '    if len(candidates) < _before:\n'
    '        log.info(f"AI pick: filtered {_before - len(candidates)} old candidates (older than 36h), {len(candidates)} remain")\n'
    '    candidates.sort(key=lambda a: a.get("pub_date",""), reverse=True)\n'
    '    if len(candidates) > 50:\n'
    '        candidates = candidates[:50]\n'
    '        log.info(f"AI pick: capped to 50 newest candidates")\n'
    '    if not candidates:\n'
    '        log.info("AI pick: no candidates within last 36h — nothing to score")\n'
    '        with sqlite3.connect(DB_PATH) as _rx:\n'
    '            _rx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES (?, ?)", (_gate_key, _today))\n'
    '        return [], []\n'
)
new_cap = (
    '    # Filter to last 36h, then apply per-source caps for fair representation\n'
    '    # FT: up to 30 newest; FA: up to 15 newest; Economist: all (small number)\n'
    '    from datetime import datetime as _dt, timezone as _tz, timedelta as _td\n'
    '    _cutoff = (_dt.now(_tz.utc) - _td(hours=36)).strftime("%Y-%m-%d")\n'
    '    _before = len(candidates)\n'
    '    candidates = [a for a in candidates if not a.get("pub_date") or a.get("pub_date","") >= _cutoff]\n'
    '    if len(candidates) < _before:\n'
    '        log.info(f"AI pick: filtered {_before - len(candidates)} old candidates (older than 36h), {len(candidates)} remain")\n'
    '    def _cap_source(cands, source, limit):\n'
    '        sc = sorted([c for c in cands if c.get("source") == source],\n'
    '                    key=lambda a: a.get("pub_date",""), reverse=True)\n'
    '        return sc[:limit]\n'
    '    _ft_cands  = _cap_source(candidates, "Financial Times", 30)\n'
    '    _fa_cands  = _cap_source(candidates, "Foreign Affairs", 15)\n'
    '    _eco_cands = [c for c in candidates if c.get("source") == "The Economist"]\n'
    '    candidates = _ft_cands + _fa_cands + _eco_cands\n'
    '    log.info(f"AI pick: per-source caps — FT:{len(_ft_cands)} FA:{len(_fa_cands)} Eco:{len(_eco_cands)} total:{len(candidates)}")\n'
    '    if not candidates:\n'
    '        log.info("AI pick: no candidates within last 36h — nothing to score")\n'
    '        with sqlite3.connect(DB_PATH) as _rx:\n'
    '            _rx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES (?, ?)", (_gate_key, _today))\n'
    '        return [], []\n'
)

assert old_cap in content, "cap block not found"
content = content.replace(old_cap, new_cap, 1)
print("Per-source caps applied")

ast.parse(content)
print("Syntax OK")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
