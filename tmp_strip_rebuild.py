
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# Replace the entire info-strip content with the rich horizontal panel
old_strip = '''<div id="info-strip" style="display:none;align-items:flex-start;gap:0;padding:14px 24px;background:var(--paper);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap;overflow-x:auto;position:sticky;top:184px;z-index:51;isolation:isolate;">
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

new_strip = '''<div id="info-strip" style="display:none;flex-direction:row;align-items:flex-start;gap:0;padding:14px 24px;background:var(--paper);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap;overflow-x:auto;position:sticky;top:184px;z-index:51;isolation:isolate;scrollbar-width:none;">

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

  <!-- ① Key numbers -->
  <div style="flex-shrink:0;margin-right:28px;">
    <div style="display:flex;gap:20px;align-items:flex-end;">
      <div><div id="stat-total" style="font-size:20px;font-weight:600;color:var(--ink);line-height:1;">–</div><div style="font-size:10px;color:var(--ink-3);margin-top:2px;">Total</div></div>
      <div><div id="stat-saves" style="font-size:20px;font-weight:600;color:var(--ink);line-height:1;">–</div><div style="font-size:10px;color:var(--ink-3);margin-top:2px;">My saves</div></div>
      <div><div id="stat-ai" style="font-size:20px;font-weight:600;color:var(--ink);line-height:1;">–</div><div style="font-size:10px;color:var(--ink-3);margin-top:2px;">AI picks</div></div>
      <div><div id="stat-ft" style="font-size:20px;font-weight:600;color:var(--green);line-height:1;">–</div><div style="font-size:10px;color:var(--ink-3);margin-top:2px;">Full text</div></div>
    </div>
  </div>

  <div style="width:0.5px;background:var(--rule);align-self:stretch;margin:0 24px;flex-shrink:0;"></div>

  <!-- ② Curation donut -->
  <div style="flex-shrink:0;margin-right:28px;">
    <div style="font-size:9px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink-3);margin-bottom:8px;">Curation</div>
    <div style="display:flex;align-items:center;gap:12px;">
      <svg id="stat-donut" width="48" height="48" viewBox="0 0 48 48" style="flex-shrink:0;">
        <circle cx="24" cy="24" r="18" fill="none" stroke="var(--paper-3)" stroke-width="9"/>
        <circle id="donut-saves" cx="24" cy="24" r="18" fill="none" stroke="var(--ink)" stroke-width="9" stroke-dasharray="0 113.1" stroke-dashoffset="28.3" stroke-linecap="butt"/>
        <circle id="donut-ai" cx="24" cy="24" r="18" fill="none" stroke="var(--accent)" stroke-width="9" stroke-dasharray="0 113.1" stroke-dashoffset="28.3" stroke-linecap="butt"/>
        <text id="donut-pct" x="24" y="27" text-anchor="middle" font-size="9" font-family="IBM Plex Sans,sans-serif" fill="var(--ink)" font-weight="600">–%</text>
      </svg>
      <div style="display:flex;flex-direction:column;gap:4px;">
        <div style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--ink-2);white-space:nowrap;"><div style="width:8px;height:8px;border-radius:2px;background:var(--ink);flex-shrink:0;"></div>My saves — <span id="leg-saves">–</span></div>
        <div style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--ink-2);white-space:nowrap;"><div style="width:8px;height:8px;border-radius:2px;background:var(--accent);flex-shrink:0;"></div>AI picks — <span id="leg-ai">–</span></div>
      </div>
    </div>
  </div>

  <div style="width:0.5px;background:var(--rule);align-self:stretch;margin:0 24px;flex-shrink:0;"></div>

  <!-- ③ Source bars -->
  <div style="flex-shrink:0;margin-right:28px;min-width:200px;">
    <div style="font-size:9px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink-3);margin-bottom:8px;">By source</div>
    <div id="stat-src-bars"></div>
  </div>

  <div style="width:0.5px;background:var(--rule);align-self:stretch;margin:0 24px;flex-shrink:0;"></div>

  <!-- ④ Full text coverage -->
  <div style="flex-shrink:0;margin-right:28px;min-width:180px;">
    <div style="font-size:9px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink-3);margin-bottom:8px;">Full text coverage</div>
    <div id="stat-cov-bars"></div>
  </div>

  <div style="width:0.5px;background:var(--rule);align-self:stretch;margin:0 24px;flex-shrink:0;"></div>

  <!-- ⑤ Top topics -->
  <div style="flex-shrink:0;margin-right:28px;min-width:150px;">
    <div style="font-size:9px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink-3);margin-bottom:8px;">Top topics</div>
    <div id="stat-topics"></div>
  </div>

  <div style="width:0.5px;background:var(--rule);align-self:stretch;margin:0 24px;flex-shrink:0;"></div>

  <!-- ⑥ Last 24h — plain text, no pills/borders -->
  <div style="flex-shrink:0;">
    <div style="font-size:9px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink-3);margin-bottom:8px;">Last 24 hours</div>
    <div id="stat-24h" style="display:flex;flex-direction:column;gap:4px;"></div>
  </div>

</div>'''

if old_strip in html:
    html = html.replace(old_strip, new_strip)
    results.append('info-strip full panel: OK')
else:
    results.append('info-strip: NOT FOUND — checking partial')
    # Try matching just the opening
    if 'id="info-strip"' in html and 'id="tally-saves"' in html and 'id="stat-total"' not in html:
        results.append('already has old simple strip — different text, manual fix needed')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
