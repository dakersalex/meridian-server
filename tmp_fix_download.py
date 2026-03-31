"""
Fix downloadBriefPDF: open a blank window immediately on click (counts as user gesture),
then navigate it to the PDF URL once the job is done. This avoids the popup blocker
entirely since the window.open() is synchronous with the button click.
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

    // Trigger download via location.href — avoids Chrome popup blocker
    // Content-Disposition: attachment means the file downloads without navigating away
    window.location.href = SERVER + '/api/kt/brief/pdf/download/' + jobId;

    if (btn) { btn.disabled = false; btn.innerHTML = origLabel; }
    toast('PDF downloaded');

  } catch(e) {
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

assert OLD in src, "Function not found — may have changed"
src = src.replace(OLD, NEW, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Patched OK")
