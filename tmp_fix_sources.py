
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

old = '''  const srcEntries=Object.entries(sc).sort((a,b)=>b[1]-a[1]).slice(0,8);
  const ftCounts={};articles.forEach(a=>{if(a.status==='full_text')ftCounts[a.source]=(ftCounts[a.source]||0)+1;});
  const totalAll=srcEntries.reduce((s,[,c])=>s+c,0);
  const totalFt=srcEntries.reduce((s,[src])=>s+(ftCounts[src]||0),0);'''

new = '''  const allSrcEntries=Object.entries(sc).sort((a,b)=>b[1]-a[1]);
  const srcEntries=allSrcEntries.slice(0,6);
  const otherEntries=allSrcEntries.slice(6);
  const ftCounts={};articles.forEach(a=>{if(a.status==='full_text')ftCounts[a.source]=(ftCounts[a.source]||0)+1;});
  const totalAll=articles.length;
  const totalFt=Object.values(ftCounts).reduce((s,c)=>s+c,0);
  const otherCount=otherEntries.reduce((s,[,c])=>s+c,0);
  const otherFt=otherEntries.reduce((s,[src])=>s+(ftCounts[src]||0),0);'''

if old in html:
    html = html.replace(old, new)
    print('Part 1 patched OK')
else:
    print('Part 1 NOT FOUND')

# Add the "Other" row before the footer
old2 = '''  const rows=srcEntries.map(([s,c])=>`<div class="source-row"><div class="source-dot" style="background:${sourceColor(s)}"></div><span class="source-name" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:110px" title="${s}">${shortName(s)}</span><span class="source-count" style="width:48px;text-align:right">${c}</span><span class="source-count" style="width:60px;text-align:right;color:var(--ink-3)">${ftCounts[s]||0}</span></div>`).join('');'''

new2 = '''  const rows=srcEntries.map(([s,c])=>`<div class="source-row"><div class="source-dot" style="background:${sourceColor(s)}"></div><span class="source-name" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:110px" title="${s}">${shortName(s)}</span><span class="source-count" style="width:48px;text-align:right">${c}</span><span class="source-count" style="width:60px;text-align:right;color:var(--ink-3)">${ftCounts[s]||0}</span></div>`).join('');
  const otherRow=otherCount>0?`<div class="source-row"><div class="source-dot" style="background:var(--ink-3)"></div><span class="source-name" style="color:var(--ink-3)">Other</span><span class="source-count" style="width:48px;text-align:right;color:var(--ink-3)">${otherCount}</span><span class="source-count" style="width:60px;text-align:right;color:var(--ink-3)">${otherFt}</span></div>`:'';'''

if old2 in html:
    html = html.replace(old2, new2)
    print('Part 2 patched OK')
else:
    print('Part 2 NOT FOUND')

# Update footer to use otherRow
old3 = '''  const header=\'<div class="source-row" style="font-size:10px;color:var(--ink-3);margin-bottom:4px"><span style="flex:1"></span><span style="width:48px;text-align:right">Total</span><span style="width:60px;text-align:right">Full text</span></div>\';
  const footer=`<div class="source-row" style="border-top:1px solid var(--rule);margin-top:4px;padding-top:4px;font-weight:500"><span class="source-name">Total</span><span class="source-count" style="width:48px;text-align:right">${totalAll}</span><span class="source-count" style="width:60px;text-align:right;color:var(--ink-3)">${totalFt}</span></div>`;
  document.getElementById(\'source-list\').innerHTML=(rows?header+rows+footer:\'<div style="font-size:12px;color:var(--ink-3)">No sources yet</div>\');'''

new3 = '''  const header=\'<div class="source-row" style="font-size:10px;color:var(--ink-3);margin-bottom:4px"><span style="flex:1"></span><span style="width:48px;text-align:right">Total</span><span style="width:60px;text-align:right">Full text</span></div>\';
  const footer=`<div class="source-row" style="border-top:1px solid var(--rule);margin-top:4px;padding-top:4px;font-weight:500"><span class="source-name">Total</span><span class="source-count" style="width:48px;text-align:right">${totalAll}</span><span class="source-count" style="width:60px;text-align:right;color:var(--ink-3)">${totalFt}</span></div>`;
  document.getElementById(\'source-list\').innerHTML=(rows?header+rows+otherRow+footer:\'<div style="font-size:12px;color:var(--ink-3)">No sources yet</div>\');'''

if old3 in html:
    html = html.replace(old3, new3)
    print('Part 3 patched OK')
else:
    print('Part 3 NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)
