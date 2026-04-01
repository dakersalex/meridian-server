"""
Fix kt/seed Call 1 by finding the block by line number and replacing it.
Avoids string matching issues with special characters.
"""
from pathlib import Path

p = Path('/Users/alexdakers/meridian-server/server.py')
lines = p.read_text().splitlines(keepends=True)

# Find the line containing the 'ONLY these fields' marker
target_start = None
for i, line in enumerate(lines):
    if 'For each theme produce a JSON object with ONLY these fields' in line:
        target_start = i - 1  # one line up is the theme_prompt = ( line
        break

if target_start is None:
    print("ERROR: marker not found")
    exit(1)

print(f"Found block starting at line {target_start + 1}")

# Find the end of the block (the closing paren after sample_ctx line)
target_end = None
for i in range(target_start, min(target_start + 30, len(lines))):
    if '"ARTICLES:\\n" + sample_ctx' in lines[i]:
        # end is the next line with )
        target_end = i + 2  # skip the sample_ctx line + closing paren line
        break

if target_end is None:
    print("ERROR: end not found")
    exit(1)

print(f"Block ends at line {target_end}")
print("Old block:")
for l in lines[target_start:target_end]:
    print(repr(l))

NEW_BLOCK = '''\
            theme_prompt = (
                "You are an intelligence analyst. Analyse these article titles (a representative sample "
                "from a corpus of " + str(total) + " articles) and identify exactly 10 "
                "dominant intelligence themes.\\n\\n"
                "For each theme produce a JSON object with ALL these fields:\\n"
                "- name (3-6 words)\\n"
                "- emoji (single emoji)\\n"
                "- keywords (array of 12-16 specific discriminating terms - named entities, proper nouns, "
                "places, organisations; avoid generic words like war, military, economy, geopolitics)\\n"
                "- overview (2-3 sentences)\\n"
                "- subtopics (array of 5-7 strings)\\n"
                "- key_facts (array of exactly 10 objects, each with title (short label) and "
                "body (1-2 sentences; use **bold** for key figures/stats))\\n"
                "- subtopic_details (object mapping each subtopic name to array of 4-6 bullet strings)\\n\\n"
                "Return ONLY a valid JSON array of 10 theme objects. No markdown, no preamble.\\n\\n"
                "ARTICLES:\\n" + sample_ctx
            )
            resp1 = call_anthropic({
                "model": "claude-sonnet-4-6",
                "max_tokens": 8000,
                "messages": [{"role": "user", "content": theme_prompt}]
            }, timeout=120, retries=2)
'''

new_lines = lines[:target_start] + [NEW_BLOCK] + lines[target_end:]
p.write_text(''.join(new_lines))
print(f"Patched OK — replaced lines {target_start+1} to {target_end}")
