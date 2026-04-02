import re

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    src = f.read()

# ── Patch 1: Update theme_prompt to request 8 consolidated themes ──
OLD1 = '''            theme_prompt = (
                "You are an intelligence analyst. Analyse these article titles (a representative sample "
                "from a corpus of " + str(total) + " articles) and identify exactly 10 "
                "dominant intelligence themes.\\n\\n"
                "For each theme produce a JSON object with ONLY these fields:\\n"
                "- name (3-6 words)\\n"
                "- emoji (single emoji)\\n"
                "- keywords (array of 12-16 specific discriminating terms - named entities, proper nouns, "
                "places, organisations; avoid generic words like war, military, economy, geopolitics)\\n"
                "- overview (2-3 sentences)\\n"
                "- subtopics (array of 5-7 strings)\\n\\n"
                "Do NOT include key_facts or subtopic_details - these are generated separately.\\n\\n"
                "Return ONLY a valid JSON array of 10 theme objects. No markdown, no preamble.\\n\\n"
                "ARTICLES:\\n" + sample_ctx
            )'''

NEW1 = '''            theme_prompt = (
                "You are an intelligence analyst. Analyse these article titles (a representative sample "
                "from a corpus of " + str(total) + " articles) and identify exactly 8 "
                "dominant intelligence themes.\\n\\n"
                "CONSOLIDATION RULES (strictly enforced):\\n"
                "- NEVER create two themes for the same geographic theatre. "
                "If articles cover both Iran/Gulf military conflict AND Iran/Gulf energy disruption, "
                "merge them into one theme covering both dimensions.\\n"
                "- NEVER create two themes for the same technology competition. "
                "If articles cover both Western AI industry (Nvidia/Google/OpenAI) AND China AI "
                "competition (DeepSeek/semiconductors), merge into one theme covering the full AI race.\\n"
                "- Each theme must be clearly distinct — a senior analyst should not need to read two "
                "themes to understand one coherent story.\\n"
                "- Only create a theme if article volume clearly sustains it. "
                "Prefer 8 broad, well-populated themes over 10 narrow or overlapping ones.\\n"
                "- Consumer/luxury themes should only appear if they constitute a major share of articles; "
                "otherwise absorb into a broader economics/demographics theme.\\n\\n"
                "For each theme produce a JSON object with ONLY these fields:\\n"
                "- name (3-6 words)\\n"
                "- emoji (single emoji)\\n"
                "- keywords (array of 12-16 specific discriminating terms — named entities, proper nouns, "
                "places, organisations, specific technical terms; strictly avoid generic words like "
                "war, military, conflict, economy, geopolitics, policy, crisis, markets, global, "
                "international that appear across many themes)\\n"
                "- overview (2-3 sentences)\\n"
                "- subtopics (array of 5-7 strings)\\n\\n"
                "Do NOT include key_facts or subtopic_details — generated separately.\\n\\n"
                "Return ONLY a valid JSON array of exactly 8 theme objects. No markdown, no preamble.\\n\\n"
                "ARTICLES:\\n" + sample_ctx
            )'''

# ── Patch 2: Remove duplicate call_anthropic for resp1 ──
OLD2 = '''            resp1 = call_anthropic({
                "model": "claude-sonnet-4-6",
                "max_tokens": 3000,
                "messages": [{"role": "user", "content": theme_prompt}]
            }, timeout=60, retries=2)
            resp1 = call_anthropic({
                "model": "claude-sonnet-4-6",
                "max_tokens": 3000,
                "messages": [{"role": "user", "content": theme_prompt}]
            }, timeout=60, retries=2)'''

NEW2 = '''            resp1 = call_anthropic({
                "model": "claude-sonnet-4-6",
                "max_tokens": 3000,
                "messages": [{"role": "user", "content": theme_prompt}]
            }, timeout=60, retries=2)'''

results = []

if OLD1 in src:
    src = src.replace(OLD1, NEW1)
    results.append("Patch 1 (theme_prompt): OK")
else:
    results.append("Patch 1 (theme_prompt): FAILED - string not found")

if OLD2 in src:
    src = src.replace(OLD2, NEW2)
    results.append("Patch 2 (duplicate resp1): OK")
else:
    results.append("Patch 2 (duplicate resp1): FAILED - string not found")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(src)

for r in results:
    print(r)
