"""
Patch the kt_generate seeding prompt to request specific, discriminating keywords —
named entities, places, organisations — not broad generic terms.
"""
from pathlib import Path

p = Path('/Users/alexdakers/meridian-server/server.py')
src = p.read_text()

OLD = (
    '"You are an intelligence analyst. Analyse these article titles and identify exactly 10 "\n'
    '                "dominant intelligence themes. For each produce a JSON object with: "\n'
    '                "name (3-6 words), emoji, keywords (8-12 item array), overview (2-3 sentences), "\n'
    '                "key_facts (array of 10 objects each with title and body; use **bold** markdown for key figures/stats in body), subtopics (5-7 strings), "\n'
    '                "subtopic_details (object mapping subtopic name to array of 4-6 bullet strings). "\n'
    '                "Return ONLY a valid JSON array of 10 objects. No markdown, no preamble.\\n\\n"\n'
    '                "ARTICLES:\\n" + ctx\n'
    '            )'
)

NEW = (
    '"You are an intelligence analyst. Analyse these article titles and identify exactly 10 "\n'
    '                "dominant intelligence themes. For each produce a JSON object with: "\n'
    '                "name (3-6 words), emoji, "\n'
    '                "keywords (array of 12-16 specific discriminating terms — use named entities, "\n'
    '                "proper nouns, places, organisations, and specific technical terms that ONLY appear "\n'
    '                "in articles genuinely about this theme. Avoid generic words like \'war\', \'military\', "\n'
    '                "\'conflict\', \'economy\', \'geopolitics\', \'policy\', \'markets\' that appear across many themes. "\n'
    '                "For example, for an Iran war theme use: Iran, IRGC, Hormuz, Revolutionary Guard, "\n'
    '                "Khamenei, Strait, Tehran, Houthi, sanctions, ceasefire, airstrike, Persian Gulf), "\n'
    '                "overview (2-3 sentences), "\n'
    '                "key_facts (array of 10 objects each with title and body; use **bold** markdown for key figures/stats in body), subtopics (5-7 strings), "\n'
    '                "subtopic_details (object mapping subtopic name to array of 4-6 bullet strings). "\n'
    '                "Return ONLY a valid JSON array of 10 objects. No markdown, no preamble.\\n\\n"\n'
    '                "ARTICLES:\\n" + ctx\n'
    '            )'
)

assert OLD in src, "OLD not found"
src = src.replace(OLD, NEW, 1)
p.write_text(src)
print("Patched prompt OK")
