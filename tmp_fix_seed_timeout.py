"""
Fix kt/seed timeout: split into two calls.
Call 1: themes only (name, emoji, keywords, overview, subtopics) - fast
Call 2: key_facts + subtopic_details per theme - separate call, longer timeout
"""
from pathlib import Path

p = Path('/Users/alexdakers/meridian-server/server.py')
lines = p.read_text().splitlines(keepends=True)

# Find the theme_prompt block
start = None
for i, line in enumerate(lines):
    if 'theme_prompt = (' in line and 'ALL these fields' not in ''.join(lines[max(0,i-1):i+3]):
        # This is our target — the one inside kt/seed
        # Verify by checking nearby context
        context = ''.join(lines[max(0,i-5):i+2])
        if 'sample_ctx' in ''.join(lines[i:i+25]):
            start = i
            break

if start is None:
    # fallback: find by unique marker
    for i, line in enumerate(lines):
        if 'ALL these fields' in line:
            # Walk back to find theme_prompt = (
            for j in range(i, max(0, i-5), -1):
                if 'theme_prompt = (' in lines[j]:
                    start = j
                    break
            break

if start is None:
    print("ERROR: could not find theme_prompt block")
    exit(1)

# Find the end of the resp1 call (closing }) after theme_prompt
end = None
for i in range(start, min(start+40, len(lines))):
    if '}, timeout=120, retries=2)' in lines[i] or '}, timeout=60, retries=2)' in lines[i]:
        end = i + 1
        break

if end is None:
    print("ERROR: could not find end of resp1 block")
    exit(1)

print(f"Replacing lines {start+1} to {end} ({end-start} lines)")
print("Old block:")
print(''.join(lines[start:end]))

NEW_BLOCK = '''\
            theme_prompt = (
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
            )
            resp1 = call_anthropic({
                "model": "claude-sonnet-4-6",
                "max_tokens": 3000,
                "messages": [{"role": "user", "content": theme_prompt}]
            }, timeout=60, retries=2)
'''

new_lines = lines[:start] + [NEW_BLOCK] + lines[end:]
p.write_text(''.join(new_lines))
print("Phase 1 prompt fixed OK")
