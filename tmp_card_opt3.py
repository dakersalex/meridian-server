
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# ── 1. autoPill — AI pick becomes uppercase, no italic
old_pill = "    const autoPill=a.auto_saved?'<span style=\"font-size:11px;color:var(--ink-3);font-style:italic;opacity:0.75\">ai</span>':'';"
new_pill = "    const autoPill=a.auto_saved?'AI pick':'My save';"
if old_pill in html:
    html = html.replace(old_pill, new_pill)
    results.append('autoPill: OK')
else:
    results.append('autoPill: NOT FOUND')

# ── 2. Add CSS for the option-3 two-column card layout
old_card_css = '.article-card { padding: 16px 0; margin-bottom: 2px; border-bottom: 1px solid var(--rule); cursor: pointer; transition: opacity 0.15s; }'
new_card_css = '''.article-card { padding: 0; margin-bottom: 2px; border-bottom: 1px solid var(--rule); cursor: pointer; transition: opacity 0.15s; }
.card-inner { display: flex; gap: 16px; padding: 16px 20px; }
.card-date-col { width: 44px; flex-shrink: 0; padding-top: 1px; text-align: left; }
.card-date-day { font-size: 11px; font-weight: 500; color: var(--ink-3); line-height: 1.3; }
.card-date-yr { font-size: 10px; color: var(--ink-3); opacity: 0.6; }
.card-body { flex: 1; min-width: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.card-source-topic { display: flex; align-items: center; gap: 5px; min-width: 0; }
.card-del { width: 20px; height: 20px; background: var(--paper-2); border: 0.5px solid var(--rule); border-radius: 3px; display: flex; align-items: center; justify-content: center; font-size: 10px; color: var(--ink-3); cursor: pointer; flex-shrink: 0; }
.card-del:hover { background: var(--paper-3); color: var(--ink); }
.card-footer { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
.card-badges { display: flex; gap: 5px; flex-shrink: 0; }
.curation-badge { font-size: 10px; padding: 1px 6px; border-radius: 2px; font-weight: 500; }
.curation-ai { background: #f5ede4; color: #854f0b; border: 0.5px solid #e8c9a8; }
.curation-my { background: var(--paper-3); color: var(--ink-3); border: 0.5px solid var(--rule); }'''
if old_card_css in html:
    html = html.replace(old_card_css, new_card_css)
    results.append('article-card CSS: OK')
else:
    results.append('article-card CSS: NOT FOUND')

# featured-card same treatment
old_feat_css = '.featured-card { background: var(--paper-2); border: none; border-bottom: 1px solid var(--rule); padding: 16px 0; margin-bottom: 2px; cursor: pointer; transition: opacity 0.15s; }'
new_feat_css = '.featured-card { background: var(--paper-2); border: none; border-bottom: 1px solid var(--rule); padding: 0; margin-bottom: 2px; cursor: pointer; transition: opacity 0.15s; }'
if old_feat_css in html:
    html = html.replace(old_feat_css, new_feat_css)
    results.append('featured-card CSS: OK')
else:
    results.append('featured-card CSS: NOT FOUND')

# ── 3. Rewrite featured card (i===0) — Option 3 layout
old_featured = '''if(i===0){html+=`<div class="featured-card${a.auto_saved?' ai-pick':''}" style="position:relative;padding-top:18px" data-id="${a.id}" onclick="openDetail('${a.id}')"><button onclick="event.stopPropagation();deleteArticle('${a.id}')" style="position:absolute;top:4px;right:6px;background:none;border:none;color:var(--ink-3);cursor:pointer;font-size:11px;padding:2px 4px;opacity:0.3;line-height:1" title="Delete">✕</button><div class="article-meta"><span class="source-label">${a.source}</span><span style="color:var(--rule);font-size:11px">·</span>${a.topic?`<span style="font-size:11px;color:var(--accent)">${a.topic}</span>`+`<span style="color:var(--rule);font-size:11px">·</span>`:''} ${autoPill}<span class="article-date-label" style="margin-left:auto;font-size:11px;color:var(--ink-3)">${formatPubDate(a)}</span><span class="status-badge ${a.status==='full_text'?'full-text':'title-only'}" style="margin-left:6px">${a.status==='full_text'?'Full text':'Title only'}</span></div><div class="featured-title">${a.title}</div><div class="featured-summary">${a.summary}</div>${folderName?`<div style="margin-top:8px"><span class="folder-badge">📁 ${folderName}</span></div>`:''}${sug}</div>`;}'''

new_featured = '''if(i===0){
  const [fDay,fMon,fYr]=formatPubDate(a).split(' ');
  html+=`<div class="featured-card${a.auto_saved?' ai-pick':''}" data-id="${a.id}" onclick="openDetail('${a.id}')"><div class="card-inner"><div class="card-date-col"><div class="card-date-day">${fDay||''}</div><div class="card-date-day">${fMon||''}</div><div class="card-date-yr">${fYr||''}</div></div><div class="card-body"><div class="card-header"><div class="card-source-topic"><span class="source-label">${a.source}</span>${a.topic?`<span style="color:var(--rule);font-size:11px;margin:0 2px">·</span><span style="font-size:11px;color:var(--accent)">${a.topic}</span>`:''}</div><button onclick="event.stopPropagation();deleteArticle('${a.id}')" class="card-del" title="Delete">✕</button></div><div class="featured-title">${a.title}</div><div class="featured-summary">${a.summary}</div><div class="card-footer"><div class="card-badges"><span class="status-badge ${a.status==='full_text'?'full-text':'title-only'}">${a.status==='full_text'?'Full text':'Title only'}</span><span class="curation-badge ${a.auto_saved?'curation-ai':'curation-my'}">${autoPill}</span></div><div class="article-tags">${(a.tags||[]).map(t=>`<span class="tag">${t}</span>`).join('')}</div></div>${folderName?`<div style="margin-top:6px"><span class="folder-badge">📁 ${folderName}</span></div>`:''}</div></div>${sug}</div>`;}'''

if old_featured in html:
    html = html.replace(old_featured, new_featured)
    results.append('featured card: OK')
else:
    results.append('featured card: NOT FOUND')

# ── 4. Rewrite regular card — Option 3 layout
old_reg = '''else{html+=`<div class="article-card${a.auto_saved?' ai-pick':''}" style="position:relative;padding-top:16px" data-id="${a.id}" onclick="openDetail('${a.id}')"><button onclick="event.stopPropagation();deleteArticle('${a.id}')" style="position:absolute;top:4px;right:6px;background:none;border:none;color:var(--ink-3);cursor:pointer;font-size:11px;padding:2px 4px;opacity:0.3;line-height:1" title="Delete">✕</button><div class="article-meta"><span class="source-label">${a.source}</span><span style="color:var(--rule);font-size:11px">·</span>${a.topic?`<span style="font-size:11px;color:var(--accent)">${a.topic}</span>`+`<span style="color:var(--rule);font-size:11px">·</span>`:''} ${autoPill}<span class="article-date-label" style="margin-left:auto;font-size:11px;color:var(--ink-3)">${formatPubDate(a)}</span><span class="status-badge ${a.status==='full_text'?'full-text':'title-only'}" style="margin-left:6px">${a.status==='full_text'?'Full text':'Title only'}</span></div><div class="article-title">${a.title}${a.url?'<a href="'+a.url+'" target="_blank" onclick="event.stopPropagation()" style="font-size:11px;color:var(--ink-3);text-decoration:none;margin-left:5px">↗</a>':''}</div><div class="article-summary">${a.summary}</div><div class="article-footer"><div class="article-tags">${(a.tags||[]).map(t=>`<span class="tag">${t}</span>`).join('')}</div>${folderName?`<span class="folder-badge">📁 ${folderName}</span>`:''}</div>${sug}</div>`;}'''

new_reg = '''else{
  const [rDay,rMon,rYr]=formatPubDate(a).split(' ');
  html+=`<div class="article-card${a.auto_saved?' ai-pick':''}" data-id="${a.id}" onclick="openDetail('${a.id}')"><div class="card-inner"><div class="card-date-col"><div class="card-date-day">${rDay||''}</div><div class="card-date-day">${rMon||''}</div><div class="card-date-yr">${rYr||''}</div></div><div class="card-body"><div class="card-header"><div class="card-source-topic"><span class="source-label">${a.source}</span>${a.topic?`<span style="color:var(--rule);font-size:11px;margin:0 2px">·</span><span style="font-size:11px;color:var(--accent)">${a.topic}</span>`:''}</div><button onclick="event.stopPropagation();deleteArticle('${a.id}')" class="card-del" title="Delete">✕</button></div><div class="article-title">${a.title}${a.url?'<a href="'+a.url+'" target="_blank" onclick="event.stopPropagation()" style="font-size:11px;color:var(--ink-3);text-decoration:none;margin-left:5px">↗</a>':''}</div><div class="article-summary">${a.summary}</div><div class="card-footer"><div class="card-badges"><span class="status-badge ${a.status==='full_text'?'full-text':'title-only'}">${a.status==='full_text'?'Full text':'Title only'}</span><span class="curation-badge ${a.auto_saved?'curation-ai':'curation-my'}">${autoPill}</span></div><div class="article-tags">${(a.tags||[]).map(t=>`<span class="tag">${t}</span>`).join('')}</div></div>${folderName?`<div style="margin-top:6px"><span class="folder-badge">📁 ${folderName}</span></div>`:''}</div></div>${sug}</div>`;}'''

if old_reg in html:
    html = html.replace(old_reg, new_reg)
    results.append('regular card: OK')
else:
    results.append('regular card: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
