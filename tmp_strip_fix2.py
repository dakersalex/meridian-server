
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

# ── STEP 1: Remove the orphaned stat content that sits between filter row and KEY THEMES
# It starts right after the filter row's closing </div> and ends at <!-- KEY THEMES VIEW -->
orphan_start_marker = '''  <button class="btn btn-outline" onclick="deleteSelected()" style="font-size:11px;padding:4px 8px;display:none;border-color:var(--red);color:var(--red)" id="delete-selected-btn">Delete selected</button>
</div>
    <div style="display:flex;gap:20px;align-items:flex-end;">'''

orphan_end_marker = '''<!-- KEY THEMES VIEW -->'''

start_idx = html.find(orphan_start_marker)
end_idx = html.find(orphan_end_marker)

if start_idx == -1 or end_idx == -1:
    print('ERROR: markers not found')
else:
    # Keep the filter row closing div + everything from KEY THEMES onwards
    filter_close = '''  <button class="btn btn-outline" onclick="deleteSelected()" style="font-size:11px;padding:4px 8px;display:none;border-color:var(--red);color:var(--red)" id="delete-selected-btn">Delete selected</button>
</div>
'''
    html = html[:start_idx] + filter_close + html[end_idx:]
    print('Orphan removed: OK')

# ── STEP 2: Replace the broken empty info-strip with the full correct horizontal panel
old_is = '<div id="info-strip" style="display:none;align-items:flex-start;gap:0;padding:14px 24px;background:var(--paper);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:wrap;position:sticky;top:147px;z-index:52;isolation:isolate;">'
new_is = '''<div id="info-strip" style="display:none;flex-direction:row;align-items:flex-start;gap:0;padding:14px 24px;background:var(--paper);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap;overflow-x:auto;position:sticky;top:184px;z-index:51;isolation:isolate;scrollbar-width:none;">

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

if old_is in html:
    html = html.replace(old_is, new_is)
    print('info-strip rebuilt: OK')
else:
    print('info-strip opening tag: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)
