
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update the HTML tally bar — remove Total, add pct spans
old_html = '''<div id="tally-bar" style="display:flex;align-items:center;gap:10px;padding:5px 20px;background:var(--paper-2);border-bottom:1px solid var(--rule);font-size:11px;color:var(--ink-3)">
  <span style="font-weight:500;color:var(--ink-2)">My saves:</span>
  <span id="tally-saves" style="font-weight:600;color:var(--ink)">–</span>
  <span style="color:var(--rule)">·</span>
  <span style="font-weight:500;color:var(--ink-2)">AI picks:</span>
  <span id="tally-ai" style="font-weight:600;color:var(--accent)">–</span>
  <span style="color:var(--rule)">·</span>
  <span style="font-weight:500;color:var(--ink-2)">Total:</span>
  <span id="tally-total" style="font-weight:600;color:var(--ink)">–</span>
</div>'''

new_html = '''<div id="tally-bar" style="display:flex;align-items:center;gap:10px;padding:5px 20px;background:var(--paper-2);border-bottom:1px solid var(--rule);font-size:11px;color:var(--ink-3)">
  <span style="font-weight:500;color:var(--ink-2)">My saves:</span>
  <span style="font-weight:600;color:var(--ink)"><span id="tally-saves">–</span> <span id="tally-saves-pct" style="font-weight:400;color:var(--ink-3)"></span></span>
  <span style="color:var(--rule)">·</span>
  <span style="font-weight:500;color:var(--ink-2)">AI picks:</span>
  <span style="font-weight:600;color:var(--accent)"><span id="tally-ai">–</span> <span id="tally-ai-pct" style="font-weight:400;color:var(--ink-3)"></span></span>
  <span style="display:none" id="tally-total">0</span>
</div>'''

if old_html in html:
    html = html.replace(old_html, new_html)
    print('HTML patched OK')
else:
    print('HTML NOT FOUND')

# 2. Update the JS tally population to add percentages and remove Total
old_js = '''    if (talSaves) talSaves.textContent = mySaves.toLocaleString();
    if (talAI)    talAI.textContent    = aiPicks.toLocaleString();
    if (talTotal) talTotal.textContent = allArts.length.toLocaleString();'''

new_js = '''    const talPct = (n) => allArts.length > 0 ? '(' + Math.round(n / allArts.length * 100) + '%)' : '';
    if (talSaves) talSaves.textContent = mySaves.toLocaleString();
    if (talAI)    talAI.textContent    = aiPicks.toLocaleString();
    if (talTotal) talTotal.textContent = allArts.length.toLocaleString();
    const savePctEl = document.getElementById('tally-saves-pct');
    const aiPctEl   = document.getElementById('tally-ai-pct');
    if (savePctEl) savePctEl.textContent = talPct(mySaves);
    if (aiPctEl)   aiPctEl.textContent   = talPct(aiPicks);'''

if old_js in html:
    html = html.replace(old_js, new_js)
    print('JS patched OK')
else:
    print('JS NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)
