"""
Final seed fix: use only 150 representative articles for theme generation.
494 titles is ~8000 input tokens alone — leaves no room for output.
150 titles = ~2500 input tokens, leaving plenty for 10 theme objects.
Assignments still run over all 494 in Haiku batches.
"""
from pathlib import Path

p = Path('/Users/alexdakers/meridian-server/server.py')
src = p.read_text()

OLD = '''            # ── Call 1: Generate 10 themes (no assignments) ───────────────────
            _kt_seed_jobs[job_id]["progress"] = f"Generating 10 themes from {total} articles..."
            theme_prompt = (
                "You are an intelligence analyst. Analyse these article titles and identify exactly 10 "
                "dominant intelligence themes.\\n\\n"
                "For each theme produce a JSON object with ONLY these fields:\\n"
                "- name (3-6 words)\\n"
                "- emoji (single emoji)\\n"
                "- keywords (array of 8-12 keywords)\\n"
                "- overview (2-3 sentences)\\n"
                "- subtopics (array of 5-7 strings)\\n\\n"
                "Do NOT include key_facts or subtopic_details — these are generated later on demand.\\n\\n"
                "Return ONLY a valid JSON array of 10 theme objects. No markdown, no preamble.\\n\\n"
                "ARTICLES:\\n" + ctx
            )
            resp1 = call_anthropic({
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4000,
                "messages": [{"role": "user", "content": theme_prompt}]
            }, timeout=180, retries=2)'''

NEW = '''            # ── Call 1: Generate 10 themes using a representative sample ─────
            # Use every 3rd article (evenly spread across corpus) for theme ID
            # ~165 titles = ~2500 input tokens, leaving plenty for 10 theme objects
            sample_lines = art_lines[::3][:165]
            sample_ctx = "\\n".join(sample_lines)
            _kt_seed_jobs[job_id]["progress"] = f"Identifying themes from {len(sample_lines)} representative articles..."
            theme_prompt = (
                "You are an intelligence analyst. Analyse these article titles (a representative sample "
                "from a corpus of " + str(total) + " articles) and identify exactly 10 "
                "dominant intelligence themes.\\n\\n"
                "For each theme produce a JSON object with ONLY these fields:\\n"
                "- name (3-6 words)\\n"
                "- emoji (single emoji)\\n"
                "- keywords (array of 8-12 keywords)\\n"
                "- overview (2-3 sentences)\\n"
                "- subtopics (array of 5-7 strings)\\n\\n"
                "key_facts and subtopic_details are generated later — do NOT include them.\\n\\n"
                "Return ONLY a valid JSON array of 10 theme objects. No markdown, no preamble.\\n\\n"
                "ARTICLES:\\n" + sample_ctx
            )
            resp1 = call_anthropic({
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 3000,
                "messages": [{"role": "user", "content": theme_prompt}]
            }, timeout=60, retries=2)'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print('Patch OK: representative sample for theme generation')
else:
    print('FAIL: old block not found')
    idx = src.find('Call 1: Generate 10 themes')
    print(f'Found at char: {idx}')

p.write_text(src)

import subprocess
result = subprocess.run(['python3', '-c', f'import ast; ast.parse(open("{p}").read())'],
                       capture_output=True, text=True)
print('Python syntax:', 'OK' if result.returncode == 0 else result.stderr[:200])
