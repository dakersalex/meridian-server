from pathlib import Path
p = Path('/Users/alexdakers/meridian-server/brief_pdf.py')
lines = p.read_text().splitlines(keepends=True)

# Replace the broken literal-newline snippet block (lines 437-448, 0-indexed 436-447)
fixed = [
    "        snippet = 'SOURCE: ' + a.get('source', '') + '\\nTITLE: ' + a.get('title', '') + '\\n'\n",
    "        snippet += 'SUMMARY: ' + a.get('summary', '')\n",
    "        body = (a.get('body') or '').strip()\n",
    "        if body and len(body) > 100:\n",
    "            excerpt = body[:BODY_EXCERPT].rsplit(' ', 1)[0]\n",
    "            snippet += '\\nEXCERPT: ' + excerpt + '\u2026'\n",
    "        parts.append(snippet)\n",
    "    return '\\n\\n---\\n\\n'.join(parts)\n",
]

# Verify we're replacing the right lines
print("Replacing lines 437-448:")
for i, l in enumerate(lines[436:448], 437):
    print(f"  {i}: {repr(l)}")

result = lines[:436] + fixed + lines[448:]
p.write_text(''.join(result))
print(f"Done. Total lines: {len(result)}")
