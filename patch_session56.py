import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

# Fix 1: Update the prompt to use dynamic N and tighter max_tokens
old_prompt_end = (
    '        "Respond ONLY with a flat JSON array of integer scores in the same order as input, no prose, no markdown:\\n"\n'
    '        \'[7, 4, 9, 6, 8]\'\n'
    '        "\\n\\nCandidate articles:\\n" + _articles_list\n'
    '    )\n'
)
new_prompt_end = (
    '        f"Respond ONLY with a flat JSON array of EXACTLY {len(candidates)} integers in the same order as input, no prose, no markdown:\\n"\n'
    '        + "[" + ", ".join(["7","4","9","6","8"][:len(candidates)]) + "]"\n'
    '        + "\\n\\nCandidate articles:\\n" + _articles_list\n'
    '    )\n'
)
assert old_prompt_end in content, "Prompt end not found"
content = content.replace(old_prompt_end, new_prompt_end, 1)
print("Fix 1 (dynamic N in prompt): applied")

# Fix 2: Tighten max_tokens — each score is ~2-3 tokens, 65 candidates max = ~200 tokens
old_tokens = '"max_tokens": 6000,\n        "messages": [{"role": "user", "content": _prompt}]\n    }).encode()\n    _req2 = _ur.Request(\n        "https://api.anthropic.com/v1/messages",'
new_tokens = '"max_tokens": 500,\n        "messages": [{"role": "user", "content": _prompt}]\n    }).encode()\n    _req2 = _ur.Request(\n        "https://api.anthropic.com/v1/messages",'
assert old_tokens in content, "max_tokens not found"
content = content.replace(old_tokens, new_tokens, 1)
print("Fix 2 (max_tokens 6000->500): applied")

ast.parse(content)
print("Syntax OK")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
