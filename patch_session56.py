import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

old = (
    '    _articles_list = _j.dumps([\n'
    '        {"title": a["title"], "url": a["url"], "source": a["source"],\n'
    '         "standfirst": a.get("standfirst", "")}\n'
    '        for a in candidates\n'
    '    ])\n'
    '\n'
    '    _prompt = (\n'
    '        "You are scoring news articles for a senior intelligence analyst.\\n"\n'
    '        "FOLLOWED TOPICS: " + _topics_str + ".\\n\\n"\n'
    '        + ("RECENT SAVES (use to calibrate taste):\\n" + _taste_str + "\\n\\n" if _taste_str else "")\n'
    '        + "Score each candidate article 0-10:\\n"\n'
    '        "9-10: CONCRETE BREAKING DEVELOPMENT — war starts/ends, sanctions, central bank decision, "\n'
    '        "major diplomatic event, energy crisis, market shock. Not reading it today = missed a real event.\\n"\n'
    '        "7-8: High-quality analysis — market moves, geopolitical analysis, economic policy, "\n'
    '        "AI with real-world impact (new models, defence/finance deployment, regulation).\\n"\n'
    '        "6: Relevant and interesting — essays, AI and society, analysis on followed topics.\\n"\n'
    '        "0-5: Not relevant — lifestyle, sport, celebrity, health, local politics, "\n'
    '        "company earnings unrelated to macro.\\n"\n'
    '        "CRITICAL: 9-10 = concrete event. A thoughtful essay = 6-7. "\n'
    '        "Calibrate against the recent saves above — match that taste level.\\n"\n'
    '        "Use the standfirst (subtitle) where provided to improve scoring accuracy.\\n"\n'
    '        f"Respond ONLY with a flat JSON array of EXACTLY {len(candidates)} integers in the same order as input, no prose, no markdown:\\n"\n'
    '        + "[" + ", ".join(["7","4","9","6","8"][:len(candidates)]) + "]"\n'
    '        + "\\n\\nCandidate articles:\\n" + _articles_list\n'
    '    )\n'
    '\n'
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

new = (
    '    # Filter to last 36h FIRST — prompt must be built from filtered candidates\n'
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
    '\n'
    '    # Build prompt AFTER filter — so len(candidates) and articles_list are in sync\n'
    '    _articles_list = _j.dumps([\n'
    '        {"title": a["title"], "url": a["url"], "source": a["source"],\n'
    '         "standfirst": a.get("standfirst", "")}\n'
    '        for a in candidates\n'
    '    ])\n'
    '\n'
    '    _prompt = (\n'
    '        "You are scoring news articles for a senior intelligence analyst.\\n"\n'
    '        "FOLLOWED TOPICS: " + _topics_str + ".\\n\\n"\n'
    '        + ("RECENT SAVES (use to calibrate taste):\\n" + _taste_str + "\\n\\n" if _taste_str else "")\n'
    '        + "Score each candidate article 0-10:\\n"\n'
    '        "9-10: CONCRETE BREAKING DEVELOPMENT — war starts/ends, sanctions, central bank decision, "\n'
    '        "major diplomatic event, energy crisis, market shock. Not reading it today = missed a real event.\\n"\n'
    '        "7-8: High-quality analysis — market moves, geopolitical analysis, economic policy, "\n'
    '        "AI with real-world impact (new models, defence/finance deployment, regulation).\\n"\n'
    '        "6: Relevant and interesting — essays, AI and society, analysis on followed topics.\\n"\n'
    '        "0-5: Not relevant — lifestyle, sport, celebrity, health, local politics, "\n'
    '        "company earnings unrelated to macro.\\n"\n'
    '        "CRITICAL: 9-10 = concrete event. A thoughtful essay = 6-7. "\n'
    '        "Calibrate against the recent saves above — match that taste level.\\n"\n'
    '        "Use the standfirst (subtitle) where provided to improve scoring accuracy.\\n"\n'
    '        f"Respond ONLY with a flat JSON array of EXACTLY {len(candidates)} integers in the same order as input, no prose, no markdown:\\n"\n'
    '        + "[" + ", ".join(["7","4","9","6","8"][:len(candidates)]) + "]"\n'
    '        + "\\n\\nCandidate articles:\\n" + _articles_list\n'
    '    )\n'
    '\n'
)

assert old in content, "Pattern not found"
content = content.replace(old, new, 1)

ast.parse(content)
print("Syntax OK")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
