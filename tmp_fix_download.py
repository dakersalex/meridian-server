"""
Rewrite downloadBriefPDF to show the brief as rendered text in the existing modal,
with an 'Open as PDF ↗' button at the top that opens the PDF in a new tab.
This avoids all popup blocker issues — the modal opens inline, and the PDF button
is a direct user gesture so window.open is always allowed.
"""
path = "/Users/alexdakers/meridian-server/meridian.html"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

OLD = """async function downloadBriefPDF(themeIdx, type) {
  const theme = ktThemes[themeIdx];
  const themeArts = getThemeArticles(themeIdx);
  const btnId = type === 'short' ? `kt-brief-btn-short-${themeIdx}` : `kt-brief-btn-full-${themeIdx}`;
  const btn = document.getElementById(btnId);
  const origLabel = btn ? btn.innerHTML : '';

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Generating…';
  }

  // Open a blank window NOW, synchronously with the user gesture.
  // This is allowed by Chrome. We'll navigate it to the PDF once ready.
  const pdfWin = window.open('', '_blank');
  if (pdfWin) {
    pdfWin.document.write('<html><body style="font-family:sans-serif;padding:40px;color:#555">'
      + '<p>Generating your intelligence brief — this takes about 60 seconds.</p>'
      + '<p>The PDF will load here automatically when ready.</p></body></html>');
  }

  try {
    const startResp = await fetch(SERVER + '/api/kt/brief/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ theme, articles: themeArts, type })
    });
    const startData = await startResp.json();
    if (startData.error) throw new Error(startData.error);
    const jobId = startData.job_id;

    // Poll for completion
    await new Promise((resolve, reject) => {
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        if (attempts > 80) { clearInterval(poll); reject(new Error('PDF generation timed out')); return; }
        try {
          const r = await fetch(SERVER + '/api/kt/brief/pdf/status/' + jobId, { cache: 'no-store' });
          const d = await r.json();
          if (d.status === 'done') { clearInterval(poll); resolve(); }
          else if (d.status === 'error') { clearInterval(poll); reject(new Error(d.error || 'PDF generation failed')); }
        } catch(e) { clearInterval(poll); reject(e); }
      }, 3000);
    });

    // Navigate the pre-opened window to the PDF — no popup blocker, opens inline in browser
    const pdfUrl = SERVER + '/api/kt/brief/pdf/download/' + jobId;
    if (pdfWin && !pdfWin.closed) {
      pdfWin.location.href = pdfUrl;
    } else {
      // Fallback if user closed the tab
      window.open(pdfUrl, '_blank');
    }

    if (btn) { btn.disabled = false; btn.innerHTML = origLabel; }
    toast('Brief ready — opening PDF');

  } catch(e) {
    if (pdfWin && !pdfWin.closed) pdfWin.close();
    if (btn) { btn.disabled = false; btn.innerHTML = origLabel; }
    toast('Brief failed: ' + e.message);
  }
}"""

NEW = """async function downloadBriefPDF(themeIdx, type) {
  const theme = ktThemes[themeIdx];
  const themeArts = getThemeArticles(themeIdx);
  const btnId = type === 'short' ? `kt-brief-btn-short-${themeIdx}` : `kt-brief-btn-full-${themeIdx}`;
  const btn = document.getElementById(btnId);
  const origLabel = btn ? btn.innerHTML : '';
  const isShort = type === 'short';

  // Show modal with loading state immediately
  const modal = document.getElementById('kt-brief-modal');
  const content = document.getElementById('kt-brief-modal-content');
  modal.classList.add('open');
  content.innerHTML = `<div class="kt-loading-state"><div class="spinner"></div> Generating ${isShort ? 'short' : 'full intelligence'} brief…</div>`;

  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Generating…'; }

  try {
    // Step 1: Generate the text brief for display in modal
    const textResp = await fetch(SERVER + '/api/kt/brief', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ theme, articles: themeArts, type })
    });
    const textStart = await textResp.json();
    if (textStart.error) throw new Error(textStart.error);
    const textJobId = textStart.job_id;

    // Step 2: Start the PDF job in parallel (so it's ready when they click)
    let pdfJobId = null;
    fetch(SERVER + '/api/kt/brief/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ theme, articles: themeArts, type })
    }).then(r => r.json()).then(d => { if (d.job_id) pdfJobId = d.job_id; });

    // Poll text brief
    const text = await new Promise((resolve, reject) => {
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        if (attempts > 60) { clearInterval(poll); reject(new Error('Brief timed out')); return; }
        try {
          const r = await fetch(SERVER + '/api/kt/brief/status/' + textJobId, {cache:'no-store'});
          const d = await r.json();
          if (d.status === 'done') { clearInterval(poll); resolve(d.brief || ''); }
          else if (d.status === 'error') { clearInterval(poll); reject(new Error(d.error || 'Brief failed')); }
        } catch(e) { clearInterval(poll); reject(e); }
      }, 3000);
    });

    // Render markdown to HTML
    let html = text
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
      .replace(/(<li>.*<\/li>\n?)+/gs, m => '<ul>' + m + '</ul>')
      .replace(/\n\n/g, '</p><p>');
    html = html.replace(
      /<h2>Executive Summary<\/h2>([\s\S]*?)(?=<h2>|$)/,
      (m, body) => `<h2>Executive Summary</h2><div class="kt-brief-exec">${body.trim()}</div>`
    );

    if (btn) { btn.disabled = false; btn.innerHTML = origLabel; }

    content.innerHTML = `
      <div style="margin-bottom:20px;padding-bottom:16px;border-bottom:1px solid var(--rule);display:flex;align-items:flex-start;justify-content:space-between;gap:12px">
        <div>
          <div style="font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:var(--accent);font-weight:500;margin-bottom:6px">${isShort ? 'Short Brief' : 'Full Intelligence Brief'}</div>
          <div style="font-family:'Playfair Display',serif;font-size:22px;font-weight:500">${theme.emoji} ${theme.name}</div>
          <div style="font-size:11px;color:var(--ink-3);margin-top:4px">${themeArts.length} articles · ${new Date().toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric'})}</div>
        </div>
        <button id="open-pdf-btn" onclick="openBriefPDF('${pdfJobId}')"
          style="flex-shrink:0;padding:7px 14px;background:none;border:1px solid var(--rule);color:var(--ink-3);cursor:pointer;font-family:'IBM Plex Sans',sans-serif;font-size:11px;white-space:nowrap;transition:all 0.15s"
          onmouseover="this.style.borderColor='var(--accent)';this.style.color='var(--accent)'"
          onmouseout="this.style.borderColor='var(--rule)';this.style.color='var(--ink-3)'">
          Open as PDF ↗
        </button>
      </div>
      <div class="kt-brief-content"><p>${html}</p></div>`;

  } catch(e) {
    modal.classList.remove('open');
    if (btn) { btn.disabled = false; btn.innerHTML = origLabel; }
    toast('Brief failed: ' + e.message);
  }
}

async function openBriefPDF(jobId) {
  if (!jobId) { toast('PDF still generating — try again in a moment'); return; }
  const btn = document.getElementById('open-pdf-btn');
  if (btn) { btn.textContent = 'Generating PDF…'; btn.disabled = true; }
  // Poll until PDF job is ready (it's been running in parallel)
  let attempts = 0;
  while (attempts < 60) {
    attempts++;
    try {
      const r = await fetch(SERVER + '/api/kt/brief/pdf/status/' + jobId, {cache:'no-store'});
      const d = await r.json();
      if (d.status === 'done') {
        window.open(SERVER + '/api/kt/brief/pdf/download/' + jobId, '_blank');
        if (btn) { btn.textContent = 'Open as PDF ↗'; btn.disabled = false; }
        return;
      }
      if (d.status === 'error') throw new Error(d.error || 'PDF failed');
    } catch(e) {
      if (btn) { btn.textContent = 'Open as PDF ↗'; btn.disabled = false; }
      toast('PDF failed: ' + e.message);
      return;
    }
    await new Promise(res => setTimeout(res, 2000));
  }
  if (btn) { btn.textContent = 'Open as PDF ↗'; btn.disabled = false; }
  toast('PDF timed out');
}"""

assert OLD in src, "Function not found"
src = src.replace(OLD, NEW, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Patched OK")
