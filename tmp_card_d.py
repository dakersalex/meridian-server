
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# ── 1. Replace CSS for article cards — Option D style
old_css = '''.article-meta { display: flex; align-items: center; gap: 7px; margin-bottom: 5px; flex-wrap: wrap; }
.topic-pill { font-size: 10px; font-weight: 500; padding: 2px 7px; text-transform: uppercase; letter-spacing: 0.8px; border-radius: 2px; }'''
new_css = '''.article-meta { display: flex; align-items: center; gap: 5px; margin-bottom: 7px; flex-wrap: wrap; }
.topic-pill { font-size: 10px; font-weight: 500; padding: 2px 7px; text-transform: uppercase; letter-spacing: 0.8px; border-radius: 2px; }'''
if old_css in html:
    html = html.replace(old_css, new_css)
    results.append('article-meta gap: OK')
else:
    results.append('article-meta: NOT FOUND')

old_src = '.source-label { font-size: 11px; color: var(--ink-3); }'
new_src = '.source-label { font-size: 11px; font-weight: 500; color: var(--ink-2); }'
if old_src in html:
    html = html.replace(old_src, new_src)
    results.append('source-label: OK')
else:
    results.append('source-label: NOT FOUND')

old_title = ".article-title { font-family: 'Playfair Display', serif; font-size: 17px; font-weight: 500; line-height: 1.35; margin-bottom: 5px; }"
new_title = ".article-title { font-family: 'Playfair Display', serif; font-size: 17px; font-weight: 400; line-height: 1.3; margin-bottom: 5px; color: var(--ink); }"
if old_title in html:
    html = html.replace(old_title, new_title)
    results.append('article-title: OK')
else:
    results.append('article-title: NOT FOUND')

old_sum = '.article-summary { font-size: 13px; color: var(--ink-2); line-height: 1.6; margin-bottom: 6px; }'
new_sum = '.article-summary { font-size: 12px; color: var(--ink-2); line-height: 1.6; margin-bottom: 8px; }'
if old_sum in html:
    html = html.replace(old_sum, new_sum)
    results.append('article-summary: OK')
else:
    results.append('article-summary: NOT FOUND')

old_tag = '.tag { font-size: 10px; color: var(--ink-3); border: 1px solid var(--rule); padding: 1px 5px; }'
new_tag = '.tag { font-size: 10px; color: var(--ink-3); border: 0.5px solid var(--rule); padding: 1px 5px; border-radius: 2px; }'
if old_tag in html:
    html = html.replace(old_tag, new_tag)
    results.append('tag: OK')
else:
    results.append('tag: NOT FOUND')

# Featured title — slightly larger but same weight
old_ftitle = ".featured-title { font-family: 'Playfair Display', serif; font-size: 21px; font-weight: 600; line-height: 1.25; margin-bottom: 8px; }"
new_ftitle = ".featured-title { font-family: 'Playfair Display', serif; font-size: 20px; font-weight: 400; line-height: 1.3; margin-bottom: 8px; color: var(--ink); }"
if old_ftitle in html:
    html = html.replace(old_ftitle, new_ftitle)
    results.append('featured-title: OK')
else:
    results.append('featured-title: NOT FOUND')

# Featured summary same as article summary
old_fsum = '.featured-summary { font-size: 13px; color: var(--ink-2); line-height: 1.7; }'
new_fsum = '.featured-summary { font-size: 12px; color: var(--ink-2); line-height: 1.6; }'
if old_fsum in html:
    html = html.replace(old_fsum, new_fsum)
    results.append('featured-summary: OK')
else:
    results.append('featured-summary: NOT FOUND')

# Remove featured-label CSS (no longer used)
old_flabel = '.featured-label { font-size: 10px; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 500; color: var(--accent); margin-bottom: 6px; }'
new_flabel = '.featured-label { display: none; }'
if old_flabel in html:
    html = html.replace(old_flabel, new_flabel)
    results.append('featured-label hidden: OK')
else:
    results.append('featured-label: NOT FOUND')

# ── 2. New autoPill — Option D: plain italic "ai" in the meta line, no badge
old_pill = """    const autoPill=a.auto_saved?'<span style="font-size:10px;padding:2px 7px;border-radius:10px;background:var(--accent);color:#fff;font-weight:500;letter-spacing:0.3px;margin-left:6px">✦ AI pick</span>':'<span style="font-size:10px;padding:2px 7px;border-radius:10px;background:var(--paper-3);color:var(--ink-3);font-weight:500;letter-spacing:0.3px;margin-left:6px;border:1px solid var(--rule)">My save</span>';
    const autoStyle=a.auto_saved?'':'';"""
new_pill = """    const autoPill=a.auto_saved?'<span style="font-size:11px;color:var(--ink-3);font-style:italic;opacity:0.75">ai</span>':'';
    const autoStyle='';"""
if old_pill in html:
    html = html.replace(old_pill, new_pill)
    results.append('autoPill italic: OK')
else:
    results.append('autoPill: NOT FOUND')

# ── 3. Rewrite featured card (i===0) — Option D meta line layout
# Meta line: Source · Topic · ai (italic) · date pushed right · status
old_featured_card = '''if(i===0){html+=`<div class="featured-card${a.auto_saved?' ai-pick':''}" style="position:relative;padding-top:20px" data-id="${a.id}" onclick="openDetail('${a.id}')"><div class="featured-label">Latest · ${a.source}</div><button onclick="event.stopPropagation();deleteArticle('${a.id}')" style="position:absolute;top:2px;right:6px;background:none;border:1px solid var(--rule);color:var(--ink-3);cursor:pointer;font-size:10px;padding:1px 4px;opacity:0.4;line-height:1;border-radius:2px" title="Delete">✕</button><div class="article-meta" style="margin-top:0px"><span class="source-label">${a.source}</span>${autoPill}<span class="article-date-label" style="margin-left:auto">${formatPubDate(a)}</span><span class="status-badge ${a.status==='full_text'?'full-text':'title-only'}" style="margin-left:8px">${a.status==='full_text'?'Full text':'Title only'}</span></div><div class="article-meta" style="margin-top:3px">${a.topic?`<span class="topic-pill ${topicClass(a.topic)}" style="${topicStyle(a.topic)}">${a.topic}</span>`:''}</div><div style="position:absolute;top:8px;right:8px"></div><div class="featured-title">${a.title}</div><div class="featured-summary">${a.summary}</div>${folderName?`<div style="margin-top:8px"><span class="folder-badge">📁 ${folderName}</span></div>`:''}${sug}</div>`;}'''

new_featured_card = '''if(i===0){html+=`<div class="featured-card${a.auto_saved?' ai-pick':''}" style="position:relative;padding-top:18px" data-id="${a.id}" onclick="openDetail('${a.id}')"><button onclick="event.stopPropagation();deleteArticle('${a.id}')" style="position:absolute;top:4px;right:6px;background:none;border:none;color:var(--ink-3);cursor:pointer;font-size:11px;padding:2px 4px;opacity:0.3;line-height:1" title="Delete">✕</button><div class="article-meta"><span class="source-label">${a.source}</span><span style="color:var(--rule);font-size:11px">·</span>${a.topic?`<span style="font-size:11px;color:var(--accent)">${a.topic}</span>`+`<span style="color:var(--rule);font-size:11px">·</span>`:''} ${autoPill}<span class="article-date-label" style="margin-left:auto;font-size:11px;color:var(--ink-3)">${formatPubDate(a)}</span><span class="status-badge ${a.status==='full_text'?'full-text':'title-only'}" style="margin-left:6px">${a.status==='full_text'?'Full text':'Title only'}</span></div><div class="featured-title">${a.title}</div><div class="featured-summary">${a.summary}</div>${folderName?`<div style="margin-top:8px"><span class="folder-badge">📁 ${folderName}</span></div>`:''}${sug}</div>`;}'''

if old_featured_card in html:
    html = html.replace(old_featured_card, new_featured_card)
    results.append('featured card D layout: OK')
else:
    results.append('featured card: NOT FOUND')

# ── 4. Rewrite regular card — Option D meta line layout
old_reg_card = '''else{html+=`<div class="article-card${a.auto_saved?' ai-pick':''}" style="position:relative;padding-top:20px" data-id="${a.id}" onclick="openDetail('${a.id}')"><button onclick="event.stopPropagation();deleteArticle('${a.id}')" style="position:absolute;top:2px;right:6px;background:none;border:1px solid var(--rule);color:var(--ink-3);cursor:pointer;font-size:10px;padding:1px 4px;opacity:0.4;line-height:1;border-radius:2px" title="Delete">✕</button><div class="article-meta" style="margin-top:0px"><span class="source-label">${a.source}</span>${autoPill}<span class="article-date-label" style="margin-left:auto">${formatPubDate(a)}</span><span class="status-badge ${a.status==='full_text'?'full-text':'title-only'}" style="margin-left:8px">${a.status==='full_text'?'Full text':'Title only'}</span></div><div class="article-meta" style="margin-top:3px">${a.topic?`<span class="topic-pill ${topicClass(a.topic)}" style="${topicStyle(a.topic)}">${a.topic}</span>`:''}</div><div style="position:absolute;top:8px;right:8px"></div><div class="article-title">${a.title}${a.url?'<a href="'+a.url+'" target="_blank" onclick="event.stopPropagation()" style="font-size:11px;color:var(--ink-3);text-decoration:none;margin-left:5px">↗</a>':''}</div><div class="article-summary">${a.summary}</div><div class="article-footer"><div class="article-tags">${(a.tags||[]).map(t=>`<span class="tag">${t}</span>`).join('')}</div>${folderName?`<span class="folder-badge">📁 ${folderName}</span>`:''}</div>${sug}</div>`;}'''

new_reg_card = '''else{html+=`<div class="article-card${a.auto_saved?' ai-pick':''}" style="position:relative;padding-top:16px" data-id="${a.id}" onclick="openDetail('${a.id}')"><button onclick="event.stopPropagation();deleteArticle('${a.id}')" style="position:absolute;top:4px;right:6px;background:none;border:none;color:var(--ink-3);cursor:pointer;font-size:11px;padding:2px 4px;opacity:0.3;line-height:1" title="Delete">✕</button><div class="article-meta"><span class="source-label">${a.source}</span><span style="color:var(--rule);font-size:11px">·</span>${a.topic?`<span style="font-size:11px;color:var(--accent)">${a.topic}</span>`+`<span style="color:var(--rule);font-size:11px">·</span>`:''} ${autoPill}<span class="article-date-label" style="margin-left:auto;font-size:11px;color:var(--ink-3)">${formatPubDate(a)}</span><span class="status-badge ${a.status==='full_text'?'full-text':'title-only'}" style="margin-left:6px">${a.status==='full_text'?'Full text':'Title only'}</span></div><div class="article-title">${a.title}${a.url?'<a href="'+a.url+'" target="_blank" onclick="event.stopPropagation()" style="font-size:11px;color:var(--ink-3);text-decoration:none;margin-left:5px">↗</a>':''}</div><div class="article-summary">${a.summary}</div><div class="article-footer"><div class="article-tags">${(a.tags||[]).map(t=>`<span class="tag">${t}</span>`).join('')}</div>${folderName?`<span class="folder-badge">📁 ${folderName}</span>`:''}</div>${sug}</div>`;}'''

if old_reg_card in html:
    html = html.replace(old_reg_card, new_reg_card)
    results.append('regular card D layout: OK')
else:
    results.append('regular card: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
