
path = '/Users/alexdakers/meridian-server/brief_pdf.py'
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

# Fix the call inside build_brief_pdf (line ~813)
old = '                ctx = _build_article_context(articles, brief_type)\n                prompt = _build_prompt(theme.get("name", ""), theme.get("subtopics", []),\n                                       ctx, brief_type)'
new = '                ctx, _sel_count = _build_article_context(articles, brief_type)\n                selected_count = _sel_count\n                prompt = _build_prompt(theme.get("name", ""), theme.get("subtopics", []),\n                                       ctx, brief_type)'

if old in src:
    src = src.replace(old, new)
    print('build_brief_pdf call patched OK')
else:
    print('NOT FOUND')

# Also fix the kt_brief route in server.py which calls _build_article_context directly
with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

# Now fix server.py kt_brief route
path2 = '/Users/alexdakers/meridian-server/server.py'
with open(path2, 'r', encoding='utf-8') as f:
    src2 = f.read()

old2 = '            art_context = _build_article_context(articles, brief_type)\n            prompt = _build_prompt(name, subtopics, art_context, brief_type)'
new2 = '            art_context, art_count = _build_article_context(articles, brief_type)\n            prompt = _build_prompt(name, subtopics, art_context, brief_type)'

if old2 in src2:
    src2 = src2.replace(old2, new2)
    print('server.py kt_brief patched OK')
    with open(path2, 'w', encoding='utf-8') as f:
        f.write(src2)
else:
    # Find what's actually there
    idx = src2.find('_build_article_context')
    print(f'server.py: not found, checking... idx={idx}')
    if idx >= 0:
        print(repr(src2[idx-10:idx+150]))
