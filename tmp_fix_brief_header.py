
path = '/Users/alexdakers/meridian-server/brief_pdf.py'
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

# Fix 1: _build_article_context returns (context_str, selected_count) tuple
old_return = "    return '\\n\\n---\\n\\n'.join(parts)"
new_return = "    return '\\n\\n---\\n\\n'.join(parts), len(selected)"

if old_return in src:
    src = src.replace(old_return, new_return)
    print('Return patched OK')
else:
    print('Return NOT FOUND')

# Fix 2: kt_brief route unpacks tuple
old_unpack = "            art_context = _build_article_context(articles, brief_type)\n            prompt = _build_prompt(name, subtopics, art_context, brief_type)"
new_unpack = "            art_context, art_count = _build_article_context(articles, brief_type)\n            prompt = _build_prompt(name, subtopics, art_context, brief_type)"

if old_unpack in src:
    src = src.replace(old_unpack, new_unpack)
    print('Unpack in kt_brief patched OK')
else:
    print('Unpack NOT FOUND - searching...')
    idx = src.find('_build_article_context(articles, brief_type)')
    print(f'  Found at char {idx}: {repr(src[idx-50:idx+100])}')

# Fix 3: build_brief_pdf uses selected_count for header not len(articles)
old_header = '        f"Meridian Intelligence  .  {today}  .  {len(articles)} articles"\n        f"  .  {len(sources)} sources", SM))'
new_header = '        f"Meridian Intelligence  .  {today}  .  {selected_count} articles"\n        f"  .  {len(sources)} sources", SM))'

if old_header in src:
    src = src.replace(old_header, new_header)
    print('Header patched OK')
else:
    print('Header NOT FOUND')
    idx = src.find('len(articles)} articles')
    if idx >= 0:
        print(f'  Found at: {repr(src[idx-20:idx+60])}')

# Fix 4: build_brief_pdf signature and call to _build_article_context
# build_brief_pdf receives articles + brief_type, needs to pass count through
old_sig = 'def build_brief_pdf(theme, articles, brief_text, brief_type="full", db_path=None):'
new_sig = 'def build_brief_pdf(theme, articles, brief_text, brief_type="full", db_path=None, selected_count=None):'

if old_sig in src:
    src = src.replace(old_sig, new_sig)
    print('Signature patched OK')
else:
    print('Signature NOT FOUND')

# Also add fallback: if selected_count not passed, use len(articles)
old_fallback_anchor = '    story.append(Paragraph(\n        f"Meridian Intelligence  .  {today}  .  {selected_count} articles"'
new_fallback_anchor = '    if selected_count is None:\n        selected_count = len(articles)\n    story.append(Paragraph(\n        f"Meridian Intelligence  .  {today}  .  {selected_count} articles"'

if old_fallback_anchor in src:
    src = src.replace(old_fallback_anchor, new_fallback_anchor)
    print('Fallback patched OK')
else:
    print('Fallback NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)
print('Written OK')
