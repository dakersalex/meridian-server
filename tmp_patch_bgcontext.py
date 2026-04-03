
# Patch 1: Add /api/brief/context route to server.py
path_server = '/Users/alexdakers/meridian-server/server.py'
with open(path_server, 'r', encoding='utf-8') as f:
    src = f.read()

new_route = '''
@app.route("/api/brief/context", methods=["POST"])
def brief_context():
    """Build scored article context using the same logic as brief_pdf._build_article_context.
    Accepts a list of articles and returns the pre-selected, formatted context string
    so bgGenerate can share the same selection logic as the PDF brief pipeline."""
    from brief_pdf import _build_article_context
    data = request.json or {}
    articles = data.get("articles", [])
    brief_type = data.get("brief_type", "full")
    if not articles:
        return jsonify({"context": "", "count": 0})
    context = _build_article_context(articles, brief_type)
    count = len([a for a in articles if a.get("summary")])
    return jsonify({"context": context, "count": count})

'''

# Insert before the images/backfill route
anchor = '@app.route("/api/images/recent", methods=["GET"])'
if anchor in src:
    src = src.replace(anchor, new_route + anchor)
    with open(path_server, 'w', encoding='utf-8') as f:
        f.write(src)
    print('SERVER PATCHED OK')
else:
    print('SERVER ANCHOR NOT FOUND')

# Patch 2: Update bgGenerate in meridian.html to use /api/brief/context
path_html = '/Users/alexdakers/meridian-server/meridian.html'
with open(path_html, 'r', encoding='utf-8') as f:
    html = f.read()

old_slice = '''  try {
    // Build context from filtered articles
    const maxArts = bgBriefType === 'short' ? 40 : 80;
    const contextArts = filteredArts.slice(0, maxArts);
    const context = contextArts.map(a =>
      `[${a.source}${a.pub_date ? ', ' + a.pub_date : ''}] ${a.title}: ${(a.summary||'').slice(0,300)}`
    ).join('\\n');

    const periodLabel = bgPeriodDays === 0 ? 'all available coverage'
      : bgPeriodDays === 1 ? 'last 24 hours'
      : bgPeriodDays === 7 ? 'last 7 days' : 'last 30 days';

    let userMsg = `Articles (${contextArts.length}, ${periodLabel}):\\n${context}`;
    if (focusedTopic) userMsg += `\\n\\nFocus: ${focusedTopic}`;
    if (guidance) userMsg += `\\n\\nGuidance: ${guidance}`;

    const maxTokens = bgBriefType === 'short' ? 1500 : 4000;'''

new_slice = '''  try {
    // Build context server-side using the same scored selection as the PDF pipeline
    const ctxResp = await fetch(SERVER + '/api/brief/context', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ articles: filteredArts, brief_type: bgBriefType })
    });
    const ctxData = await ctxResp.json();
    const context = ctxData.context || '';

    const periodLabel = bgPeriodDays === 0 ? 'all available coverage'
      : bgPeriodDays === 1 ? 'last 24 hours'
      : bgPeriodDays === 7 ? 'last 7 days' : 'last 30 days';

    let userMsg = `Articles (${ctxData.count || filteredArts.length}, ${periodLabel}):\\n${context}`;
    if (focusedTopic) userMsg += `\\n\\nFocus: ${focusedTopic}`;
    if (guidance) userMsg += `\\n\\nGuidance: ${guidance}`;

    const maxTokens = bgBriefType === 'short' ? 1500 : 4000;'''

if old_slice in html:
    html = html.replace(old_slice, new_slice)
    with open(path_html, 'w', encoding='utf-8') as f:
        f.write(html)
    print('HTML PATCHED OK')
else:
    print('HTML SLICE NOT FOUND')
