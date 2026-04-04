
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# ── 1. Replace info-strip HTML with Option 3 two-row layout
old_strip_open = '<div id="info-strip" style="display:none;flex-direction:row;align-items:flex-start;gap:0;padding:14px 24px;background:var(--paper);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap;overflow-x:auto;position:sticky;top:184px;z-index:51;isolation:isolate;scrollbar-width:none;">'

new_strip = '''<div id="info-strip" style="display:none;flex-direction:column;background:var(--paper);border-bottom:3px solid var(--ink);font-size:11px;position:sticky;top:184px;z-index:51;isolation:isolate;">

  <!-- hidden legacy ids needed by JS -->
  <span id="tally-saves" style="display:none">–</span>
  <span id="tally-saves-pct" style="display:none"></span>
  <span id="tally-ai" style="display:none">–</span>
  <span id="tally-ai-pct" style="display:none"></span>
  <span id="tally-total" style="display:none">0</span>
  <span id="act-ft" style="display:none">–</span>
  <span id="act-eco" style="display:none">–</span>
  <span id="act-fa" style="display:none">–</span>
  <span id="act-bbg" style="display:none">–</span>
  <span id="act-fp" style="display:none">–</span>
  <span id="act-ft-pill" style="display:none" class="activity-pill activity-pill-zero"></span>
  <span id="act-eco-pill" style="display:none" class="activity-pill activity-pill-zero"></span>
  <span id="act-fa-pill" style="display:none" class="activity-pill activity-pill-zero"></span>
  <span id="act-bbg-pill" style="display:none" class="activity-pill activity-pill-zero"></span>
  <span id="act-fp-pill" style="display:none" class="activity-pill activity-pill-zero"></span>
  <span class="activity-warning" id="act-warning" style="display:none"></span>

  <!-- TOP ROW: headline numbers + 24h activity -->
  <div style="display:flex;align-items:center;padding:12px 24px 10px;border-bottom:0.5px solid var(--rule);flex-wrap:nowrap;overflow-x:auto;gap:0;scrollbar-width:none;">
    <div style="display:flex;gap:24px;align-items:flex-end;flex-shrink:0;">
      <div><div id="stat-total" style="font-size:22px;font-weight:600;color:var(--ink);line-height:1;">–</div><div style="font-size:10px;color:var(--ink-3);margin-top:3px;white-space:nowrap;">Total articles</div></div>
      <div><div id="stat-saves" style="font-size:22px;font-weight:600;color:var(--ink);line-height:1;">–</div><div style="font-size:10px;color:var(--ink-3);margin-top:3px;white-space:nowrap;">My saves</div></div>
      <div><div id="stat-ai" style="font-size:22px;font-weight:600;color:var(--accent);line-height:1;">–</div><div style="font-size:10px;color:var(--ink-3);margin-top:3px;white-space:nowrap;">AI picks</div></div>
      <div><div id="stat-ft" style="font-size:22px;font-weight:600;color:var(--green);line-height:1;">–</div><div style="font-size:10px;color:var(--ink-3);margin-top:3px;white-space:nowrap;">Full text</div></div>
    </div>
    <div style="width:0.5px;background:var(--rule);align-self:stretch;margin:0 24px;flex-shrink:0;"></div>
    <div style="flex-shrink:0;">
      <div style="font-size:9px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--ink-3);margin-bottom:7px;white-space:nowrap;">Last 24 hours</div>
      <div id="stat-24h-top" style="display:flex;gap:16px;flex-wrap:nowrap;"></div>
    </div>
  </div>

  <!-- BOTTOM ROW: donut + topics + source bars + coverage -->
  <div style="display:flex;align-items:flex-start;gap:0;padding:12px 24px 14px;overflow-x:auto;scrollbar-width:none;">

    <!-- Donut 80px -->
    <div style="flex-shrink:0;">
      <div style="font-size:9px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink-3);margin-bottom:8px;">Curation split</div>
      <div style="display:flex;align-items:center;gap:14px;">
        <svg id="stat-donut" width="80" height="80" viewBox="0 0 80 80" style="flex-shrink:0;">
          <!-- AI arc drawn first as full ring (amber fills everything) -->
          <circle id="donut-ai" cx="40" cy="40" r="32" fill="none" stroke="var(--accent)" stroke-width="12"/>
          <!-- Saves arc on top, rotated to start at 12 o'clock via transform -->
          <circle id="donut-saves" cx="40" cy="40" r="32" fill="none" stroke="var(--ink)" stroke-width="12"
            stroke-dasharray="0 201.062"
            transform="rotate(-90 40 40)"
            stroke-linecap="butt"/>
          <text id="donut-pct" x="40" y="37" text-anchor="middle" font-size="13" font-family="IBM Plex Sans,sans-serif" fill="var(--ink)" font-weight="600">–%</text>
          <text x="40" y="51" text-anchor="middle" font-size="9" font-family="IBM Plex Sans,sans-serif" fill="var(--ink-3)">saves</text>
        </svg>
        <div style="display:flex;flex-direction:column;gap:7px;">
          <div style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--ink-2);white-space:nowrap;"><div style="width:9px;height:9px;border-radius:2px;background:var(--ink);flex-shrink:0;"></div>My saves — <span id="leg-saves" style="font-weight:600">–</span></div>
          <div style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--ink-2);white-space:nowrap;"><div style="width:9px;height:9px;border-radius:2px;background:var(--accent);flex-shrink:0;"></div>AI picks — <span id="leg-ai" style="font-weight:600">–</span></div>
        </div>
      </div>
    </div>

    <div style="width:0.5px;background:var(--rule);align-self:stretch;margin:0 24px;flex-shrink:0;"></div>

    <!-- Top 5 topics -->
    <div style="flex-shrink:0;min-width:155px;">
      <div style="font-size:9px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink-3);margin-bottom:8px;">Top topics</div>
      <div id="stat-topics"></div>
    </div>

    <div style="width:0.5px;background:var(--rule);align-self:stretch;margin:0 24px;flex-shrink:0;"></div>

    <!-- Source bars -->
    <div style="flex-shrink:0;min-width:200px;">
      <div style="font-size:9px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink-3);margin-bottom:8px;">By source</div>
      <div id="stat-src-bars"></div>
    </div>

    <div style="width:0.5px;background:var(--rule);align-self:stretch;margin:0 24px;flex-shrink:0;"></div>

    <!-- Coverage -->
    <div style="flex-shrink:0;min-width:180px;">
      <div style="font-size:9px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink-3);margin-bottom:8px;">Full text coverage</div>
      <div id="stat-cov-bars"></div>
    </div>

  </div>

</div>'''

# Find and replace the whole info-strip block
# It starts at the opening tag and ends at the closing </div> before <!-- KEY THEMES
is_start = html.find('<div id="info-strip"')
# Find the end - it's the </div> just before <!-- KEY THEMES VIEW -->
kt_marker = '<!-- KEY THEMES VIEW -->'
kt_idx = html.find(kt_marker)

if is_start == -1 or kt_idx == -1:
    results.append('info-strip bounds: NOT FOUND')
else:
    # Find the closing </div> immediately before kt_marker
    end_idx = html.rfind('</div>', is_start, kt_idx) + 6
    old_strip = html[is_start:end_idx]
    html = html[:is_start] + new_strip + html[end_idx:]
    results.append('info-strip two-row: OK')

# ── 2. Fix JS donut calculation
# Old approach: two arcs with offset maths (broken)
# New approach: AI = full ring, Saves = dasharray with transform rotate(-90)
# C for r=32: 2π×32 = 201.062
old_donut_js = '''    // Donut (circumference = 2π×18 = 113.1)
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
    if(se('donut-pct')) se('donut-pct').textContent = savesPct+'%';'''

new_donut_js = '''    // Donut — r=32, circ=2π×32=201.062
    // AI arc is drawn as full ring in HTML. Saves arc drawn on top with transform rotate(-90).
    const C = 201.062;
    const savesDash = total > 0 ? (mySavesN/total*C).toFixed(2) : '0';
    const savesPct  = total > 0 ? Math.round(mySavesN/total*100) : 0;
    if(se('donut-saves')) {
      se('donut-saves').setAttribute('stroke-dasharray', savesDash+' '+C);
    }
    if(se('donut-pct')) se('donut-pct').textContent = savesPct+'%';

    // 24h top row
    const h24Top = se('stat-24h-top');
    if(h24Top) {
      const srcColors = {'Financial Times':'#0d4a8a','The Economist':'#8b1a1a','Foreign Affairs':'#1e4d8c','Bloomberg':'#555','Foreign Policy Research Institute':'#2d6b45'};
      const srcShort = {'Financial Times':'FT','The Economist':'Economist','Foreign Affairs':'FA','Bloomberg':'Bloomberg','Foreign Policy Research Institute':'FP'};
      h24Top.innerHTML = '';
      const cutoff = Date.now() - 24*60*60*1000;
      const recent = allArts.filter(a => new Date(a.pub_date||a.saved_at).getTime() > cutoff);
      const srcMap = {};
      recent.forEach(a => { srcMap[a.source] = (srcMap[a.source]||0)+1; });
      const sources = ['Financial Times','The Economist','Foreign Affairs','Bloomberg','Foreign Policy Research Institute'];
      sources.forEach(s => {
        const n = srcMap[s]||0;
        const col = n > 0 ? (srcColors[s]||'#555') : 'var(--ink-3)';
        const lbl = srcShort[s]||s;
        const span = document.createElement('span');
        span.style.cssText = 'font-size:10px;font-weight:'+(n>0?'600':'400')+';color:'+col+';white-space:nowrap;';
        span.textContent = n > 0 ? lbl+' +'+n : lbl+' —';
        h24Top.appendChild(span);
      });
    }'''

if old_donut_js in html:
    html = html.replace(old_donut_js, new_donut_js)
    results.append('donut JS fixed: OK')
else:
    results.append('donut JS: NOT FOUND')

# ── 3. Also update stat-24h to use same data (keep for backwards compat)
# The old stat-24h div is now replaced by stat-24h-top in the new HTML

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
