with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    src = f.read()

OLD = '''                "- keywords (array of 12-16 specific discriminating terms — named entities, proper nouns, "
                "places, organisations, specific technical terms; strictly avoid generic words like "
                "war, military, conflict, economy, geopolitics, policy, crisis, markets, global, "
                "international that appear across many themes)\\n"'''

NEW = '''                "- keywords (array of 12-16 terms with this STRICT structure):\\n"
                "  * keywords[0] MUST be a SHORT, BROAD anchor word (1-2 words max) that is the single "
                "most defining term for this theme — e.g. 'Iran', 'tariffs', 'AI', 'China', 'markets'. "
                "This anchor is used as a hard gate: articles without it are excluded entirely. "
                "It must appear in titles/summaries of at least 10%% of your corpus.\\n"
                "  * keywords[1-15] are specific discriminating terms: named entities, proper nouns, "
                "places, organisations, specific technical terms that only appear in articles genuinely "
                "about this theme. Strictly avoid generic words like war, military, conflict, economy, "
                "geopolitics, policy, crisis, global, international that appear across many themes.\\n"'''

if OLD in src:
    src = src.replace(OLD, NEW)
    print("Anchor keyword prompt patch: OK")
else:
    print("FAILED — string not found")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(src)
