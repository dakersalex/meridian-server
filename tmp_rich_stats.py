
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# ── 1. Replace info-strip HTML with rich stats panel
old_strip = '''<div id="info-strip" style="display:none;align-items:center;gap:10px;padding:6px 20px;background:var(--paper);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap;position:sticky;top:147px;z-index:52;isolation:isolate;">
  <span style="color:var(--ink-2);white-space:nowrap">My saves: <strong style="color:var(--ink);font-weight:600"><span id="tally-saves">–</span></strong> <span id="tally-saves-pct" style="color:var(--ink-3)"></span></span>
  <div style="width:1px;height:12px;background:var(--rule);flex-shrink:0"></div>
  <span style="color:var(--ink-2);white-space:nowrap">AI picks: <strong style="color:var(--ink);font-weight:600"><span id="tally-ai">–</span></strong> <span id="tally-ai-pct" style="color:var(--ink-3)"></span></span>
  <div style="width:1px;height:12px;background:var(--rule);flex-shrink:0"></div>
  <span style="font-weight:500;color:var(--ink-2);white-space:nowrap">24h:</span>
  <span id="act-ft-pill" class="activity-pill activity-pill-zero"><span style="color:#0d4a8a;font-weight:500">FT</span> <span id="act-ft">–</span></span>
  <span id="act-eco-pill" class="activity-pill activity-pill-zero"><span style="color:#8b1a1a;font-weight:500">Economist</span> <span id="act-eco">–</span></span>
  <span id="act-fa-pill" class="activity-pill activity-pill-zero"><span style="color:#1e4d8c;font-weight:500">FA</span> <span id="act-fa">–</span></span>
  <span id="act-bbg-pill" class="activity-pill activity-pill-zero"><span style="color:#555;font-weight:500">Bloomberg</span> <span id="act-bbg">–</span></span>
  <span id="act-fp-pill" class="activity-pill activity-pill-zero"><span style="color:#2d6b45;font-weight:500">Foreign Policy</span> <span id="act-fp">–</span></span>
  <span class="activity-warning" id="act-warning" style="display:none">⚠ FT sync found 0 articles</span>
  <span style="display:none" id="tally-total">0</span>
</div>'''

new_strip = '''<div id="info-strip" style="display:none;align-items:flex-start;gap:0;padding:14px 24px;background:var(--paper);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:wrap;position:sticky;top:147px;z-index:52;isolation:isolate;">

  <!-- hidden spans kept for JS compatibility -->
  <span style="display:none" id="tally-saves">–</span>
  <span style="display:none" id="tally-saves-pct"></span>
  <span style="display:none" id="tally-ai">–</span>
  <span style="display:none" id="tally-ai-pct"></span>
  <span style="display:none" id="tally-total">0</span>
  <span style="display:none" id="act-ft-pill" class="activity-pill activity-pill-zero"></span>
  <span style="display:none" id="act-eco-pill" class="activity-pill activity-pill-zero"></span>
  <span style="display:none" id="act-fa-pill" class="activity-pill activity-pill-zero"></span>
  <span style="display:none" id="act-bbg-pill" class="activity-pill activity-pill-zero"></span>
  <span style="display:none" id="act-fp-pill" class="activity-pill activity-pill-zero"></span>
  <span style="display:none" id="act-ft">–</span>
  <span style="display:none" id="act-eco">–</span>
  <span style="display:none" id="act-fa">–</span>
  <span style="display:none" id="act-bbg">–</span>
  <span style="display:none" id="act-fp">–</span>
  <span style="display:none" class="activity-warning" id="act-warning"></span>

  <!-- ① Library numbers -->
  <div style="margin-right:28px;flex-shrink:0;">
    <div style="font-size:9px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink-3);margin-bottom:8px;">Library</div>
    <div style="display:flex;gap:20px;align-items:flex-end;">
      <div><div id="stat-total" style="font-size:20px;font-weight:600;color:var(--ink);line-height:1;">–</div><div style="font-size:10px;color:var(--ink-3);margin-top:2px;">Total</div></div>
      <div><div id="stat-saves" style="font-size:20px;font-weight:600;color:var(--ink);line-height:1;">–</div><div style="font-size:10px;color:var(--ink-3);margin-top:2px;">My saves</div></div>
      <div><div id="stat-ai" style="font-size:20px;font-weight:600;color:var(--ink);line-height:1;">–</div><div style="font-size:10px;color:var(--ink-3);margin-top:2px;">AI picks</div></div>
      <div><div id="stat-ft" style="font-size:20px;font-weight:600;color:var(--green);line-height:1;">–</div><div style="font-size:10px;color:var(--ink-3);margin-top:2px;">Full text</div></div>
    </div>
  </div>

  <div style="width:0.5px;background:var(--rule);align-self:stretch;margin:0 20px 0 0;flex-shrink:0;"></div>

  <!-- ② Curation donut -->
  <div style="margin-right:28px;flex-shrink:0;">
    <div style="font-size:9px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink-3);margin-bottom:8px;">Curation</div>
    <div style="display:flex;align-items:center;gap:12px;">
      <svg id="stat-donut" width="48" height="48" viewBox="0 0 48 48" style="flex-shrink:0;">
        <circle cx="24" cy="24" r="18" fill="none" stroke="var(--paper-3)" stroke-width="9"/>
        <circle id="donut-saves" cx="24" cy="24" r="18" fill="none" stroke="var(--ink)" stroke-width="9" stroke-dasharray="0 113.1" stroke-dashoffset="28.3" stroke-linecap="butt"/>
        <circle id="donut-ai" cx="24" cy="24" r="18" fill="none" stroke="var(--accent)" stroke-width="9" stroke-dasharray="0 113.1" stroke-dashoffset="28.3" stroke-linecap="butt"/>
        <text id="donut-pct" x="24" y="27" text-anchor="middle" font-size="9" font-family="IBM Plex Sans,sans-serif" fill="var(--ink)" font-weight="600">–%</text>
      </svg>
      <div style="display:flex;flex-direction:column;gap:4px;">
        <div style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--ink-2);"><div style="width:8px;height:8px;border-radius:2px;background:var(--ink);flex-shrink:0;"></div><span>My saves — <span id="leg-saves">–</span></span></div>
        <div style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--ink-2);"><div style="width:8px;height:8px;border-radius:2px;background:var(--accent);flex-shrink:0;"></div><span>AI picks — <span id="leg-ai">–</span></span></div>
      </div>
    </div>
  </div>

  <div style="width:0.5px;background:var(--rule);align-self:stretch;margin:0 20px 0 0;flex-shrink:0;"></div>

  <!-- ③ Source bars -->
  <div style="margin-right:28px;flex-shrink:0;min-width:200px;">
    <div style="font-size:9px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink-3);margin-bottom:8px;">By source</div>
    <div id="stat-src-bars"></div>
  </div>

  <div style="width:0.5px;background:var(--rule);align-self:stretch;margin:0 20px 0 0;flex-shrink:0;"></div>

  <!-- ④ Full text coverage -->
  <div style="margin-right:28px;flex-shrink:0;min-width:180px;">
    <div style="font-size:9px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink-3);margin-bottom:8px;">Full text coverage</div>
    <div id="stat-cov-bars"></div>
  </div>

  <div style="width:0.5px;background:var(--rule);align-self:stretch;margin:0 20px 0 0;flex-shrink:0;"></div>

  <!-- ⑤ Top topics -->
  <div style="margin-right:28px;flex-shrink:0;min-width:150px;">
    <div style="font-size:9px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink-3);margin-bottom:8px;">Top topics</div>
    <div id="stat-topics"></div>
  </div>

  <div style="width:0.5px;background:var(--rule);align-self:stretch;margin:0 20px 0 0;flex-shrink:0;"></div>

  <!-- ⑥ Last 24h — plain text, no pills -->
  <div style="flex-shrink:0;">
    <div style="font-size:9px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink-3);margin-bottom:8px;">Last 24 hours</div>
    <div id="stat-24h" style="display:flex;flex-direction:column;gap:4px;"></div>
  </div>

</div>'''

if old_strip in html:
    html = html.replace(old_strip, new_strip)
    results.append('info-strip: OK')
else:
    results.append('info-strip: NOT FOUND')

# ── 2. Replace the updateActivityBar JS to populate all new elements
old_activity_tail = '''    setCount('act-ft',  recent['Financial Times'] || 0);
    setCount('act-eco', recent['The Economist']   || 0);
    setCount('act-fa',  recent['Foreign Affairs'] || 0);
    setCount('act-bbg', recent['Bloomberg']       || 0);
    setCount('act-fp',  recent['Foreign Policy']  || 0);'''

new_activity_tail = '''    setCount('act-ft',  recent['Financial Times'] || 0);
    setCount('act-eco', recent['The Economist']   || 0);
    setCount('act-fa',  recent['Foreign Affairs'] || 0);
    setCount('act-bbg', recent['Bloomberg']       || 0);
    setCount('act-fp',  recent['Foreign Policy']  || 0);

    // ── Rich stats panel ──
    const total = allArts.length;
    const mySavesN = allArts.filter(a=>!a.auto_saved&&a.status!=='agent').length;
    const aiPicksN = allArts.filter(a=>a.auto_saved||a.status==='agent').length;
    const fullTextN = allArts.filter(a=>a.status==='full_text').length;

    const se = (id) => document.getElementById(id);
    if(se('stat-total')) se('stat-total').textContent = total.toLocaleString();
    if(se('stat-saves')) se('stat-saves').textContent = mySavesN.toLocaleString();
    if(se('stat-ai'))    se('stat-ai').textContent    = aiPicksN.toLocaleString();
    if(se('stat-ft'))    se('stat-ft').textContent    = fullTextN.toLocaleString();
    if(se('leg-saves'))  se('leg-saves').textContent  = mySavesN.toLocaleString();
    if(se('leg-ai'))     se('leg-ai').textContent     = aiPicksN.toLocaleString();

    // Donut (circumference = 2π×18 = 113.1)
    const C = 113.1, offset = 28.3;
    const savesDash = total > 0 ? (mySavesN/total*C).toFixed(1) : 0;
    const aiDash    = total > 0 ? (aiPicksN/total*C).toFixed(1) : 0;
    const savesPct  = total > 0 ? Math.round(mySavesN/total*100) : 0;
    if(se('donut-saves')) { se('donut-saves').setAttribute('stroke-dasharray', savesDash+' '+C); }
    if(se('donut-ai')) {
      const aiOffset = -(parseFloat(savesDash) - offset);
      se('donut-ai').setAttribute('stroke-dasharray', aiDash+' '+C);
      se('donut-ai').setAttribute('stroke-dashoffset', (-parseFloat(savesDash)+offset).toFixed(1));
    }
    if(se('donut-pct')) se('donut-pct').textContent = savesPct+'%';

    // Source bars
    const srcCounts = {}; const srcFT = {};
    allArts.forEach(a => {
      srcCounts[a.source] = (srcCounts[a.source]||0)+1;
      if(a.status==='full_text') srcFT[a.source] = (srcFT[a.source]||0)+1;
    });
    const srcSorted = Object.entries(srcCounts).sort((a,b)=>b[1]-a[1]).slice(0,5);
    const srcMax = srcSorted[0]?.[1]||1;
    const srcColors = {'The Economist':'#8b1a1a','Financial Times':'#0d4a8a','Foreign Affairs':'#1e4d8c','Bloomberg':'#555','Foreign Policy':'#2d6b45'};
    const srcEl = se('stat-src-bars');
    if(srcEl) srcEl.innerHTML = srcSorted.map(([src,n])=>{
      const w = Math.round(n/srcMax*100);
      const col = srcColors[src]||'#888';
      const short = src.replace('Financial Times','FT').replace('The Economist','Economist').replace('Foreign Affairs','FA').replace('Foreign Policy','FP');
      return `<div style="display:flex;align-items:center;gap:7px;margin-bottom:5px;">
        <div style="font-size:10px;color:var(--ink-2);width:70px;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${short}</div>
        <div style="flex:1;height:5px;background:var(--paper-3);border-radius:3px;min-width:70px;"><div style="width:${w}%;height:5px;border-radius:3px;background:${col};"></div></div>
        <div style="font-size:10px;color:var(--ink-3);width:24px;text-align:right;flex-shrink:0;">${n}</div>
      </div>`;
    }).join('');

    // Full text coverage
    const covEl = se('stat-cov-bars');
    if(covEl) covEl.innerHTML = srcSorted.filter(([s])=>srcCounts[s]>5).map(([src,n])=>{
      const ft = srcFT[src]||0;
      const pct = Math.round(ft/n*100);
      const short = src.replace('Financial Times','FT').replace('The Economist','Economist').replace('Foreign Affairs','FA').replace('Foreign Policy','FP');
      const col = pct>=95?'var(--green)':pct>=70?'var(--gold)':'var(--red)';
      return `<div style="display:flex;align-items:center;gap:7px;margin-bottom:5px;">
        <div style="font-size:10px;color:var(--ink-2);width:70px;flex-shrink:0;">${short}</div>
        <div style="flex:1;height:5px;background:var(--paper-3);border-radius:3px;overflow:hidden;min-width:70px;"><div style="width:${pct}%;height:5px;background:${col};"></div></div>
        <div style="font-size:10px;color:var(--ink-3);width:28px;text-align:right;flex-shrink:0;">${pct}%</div>
      </div>`;
    }).join('');

    // Top topics
    const topicCounts = {};
    allArts.forEach(a=>{ if(a.topic) topicCounts[a.topic]=(topicCounts[a.topic]||0)+1; });
    const topicSorted = Object.entries(topicCounts).sort((a,b)=>b[1]-a[1]).slice(0,7);
    const topicColors = ['#8b1a1a','#1e4d8c','#2d6b45','#5c2d8c','#555','#8c6a20','#c4783a'];
    const topEl = se('stat-topics');
    if(topEl) topEl.innerHTML = topicSorted.map(([t,n],i)=>
      `<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
        <div style="width:7px;height:7px;border-radius:50%;background:${topicColors[i%topicColors.length]};flex-shrink:0;"></div>
        <div style="font-size:11px;color:var(--ink-2);flex:1;">${t}</div>
        <div style="font-size:10px;color:var(--ink-3);">${n}</div>
      </div>`
    ).join('');

    // 24h activity — plain text, no pills
    const h24El = se('stat-24h');
    const sources24 = [
      {label:'Financial Times', id:'act-ft', color:'#0d4a8a'},
      {label:'Economist',       id:'act-eco',color:'#8b1a1a'},
      {label:'FA',              id:'act-fa', color:'#1e4d8c'},
      {label:'Bloomberg',       id:'act-bbg',color:'#555'},
      {label:'Foreign Policy',  id:'act-fp', color:'#2d6b45'},
    ];
    if(h24El) h24El.innerHTML = sources24.map(s=>{
      const n = recent[{'Financial Times':'Financial Times','Economist':'The Economist','FA':'Foreign Affairs','Bloomberg':'Bloomberg','Foreign Policy':'Foreign Policy'}[s.label]]||0;
      const txt = n>0 ? `+${n}` : '—';
      const col = n>0 ? 'var(--green)' : 'var(--ink-3)';
      const fw  = n>0 ? '500' : '400';
      return `<div style="font-size:11px;color:${col};font-weight:${fw};">${s.label} ${txt}</div>`;
    }).join('');'''

if old_activity_tail in html:
    html = html.replace(old_activity_tail, new_activity_tail)
    results.append('updateActivityBar rich stats: OK')
else:
    results.append('updateActivityBar: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
