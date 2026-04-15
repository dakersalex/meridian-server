import ast

with open('/Users/alexdakers/meridian-server/backfill_ai_picks.py', 'r') as f:
    content = f.read()

old_prompt = (
    '        "Respond ONLY with JSON array same order as input:\\n"\n'
    '        \'[{"score":7,"reason":"one sentence"}]\'\n'
)
new_prompt = (
    '        "Respond ONLY with a flat JSON array of integer scores same order as input:\\n"\n'
    '        \'[7, 4, 9, 6, 8]\'\n'
)
assert old_prompt in content, "Backfill prompt not found"
content = content.replace(old_prompt, new_prompt, 1)

old_route = (
    "for art, score_obj in all_scores:\n"
    "    score = score_obj.get(\"score\", 0)\n"
    "    reason = score_obj.get(\"reason\", \"\")\n"
    "    marker = \"→ FEED\" if score >= 8 else (\"→ suggested\" if score >= 6 else \"\")\n"
    "    print(f\"  [{score}] {art['title'][:65]} {marker}\")\n"
    "    if score >= 8:\n"
    "        feed_articles.append((art, score, reason))\n"
    "    elif score >= 6:\n"
    "        suggested_articles.append((art, score, reason))"
)
new_route = (
    "for art, score_obj in all_scores:\n"
    "    score = score_obj if isinstance(score_obj, int) else score_obj.get(\"score\", 0)\n"
    "    marker = \"→ FEED\" if score >= 8 else (\"→ suggested\" if score >= 6 else \"\")\n"
    "    print(f\"  [{score}] {art['title'][:65]} {marker}\")\n"
    "    if score >= 8:\n"
    "        feed_articles.append((art, score, \"\"))\n"
    "    elif score >= 6:\n"
    "        suggested_articles.append((art, score, \"\"))"
)
assert old_route in content, "Backfill route not found"
content = content.replace(old_route, new_route, 1)

# Also update parse to handle flat array
old_parse = (
    "    m = re.search(r'\\[\\[\\s\\S\\]*\\]', text)\n"
    "    scores = json.loads(m.group(0)) if m else []"
)
# Find actual parse line
import re
idx = content.find("scores = json.loads(m.group(0))")
print(f"scores parse at char: {idx}")
print(repr(content[idx-50:idx+80]))

ast.parse(content)
print("Syntax OK")
with open('/Users/alexdakers/meridian-server/backfill_ai_picks.py', 'w') as f:
    f.write(content)
print("Done")
