"""
Patch downloadBriefPDF to show rotating progress messages in both
the modal and the button while the brief is generating.
"""
path = "/Users/alexdakers/meridian-server/meridian.html"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

OLD = """  // Show modal with loading state immediately
  const modal = document.getElementById('kt-brief-modal');
  const content = document.getElementById('kt-brief-modal-content');
  modal.classList.add('open');
  content.innerHTML = `<div class="kt-loading-state"><div class="spinner"></div> Generating ${isShort ? 'short' : 'full intelligence'} brief…</div>`;

  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Generating…'; }

  try {
    // Step 1: Generate the text brief for display in modal
    const textResp = await fetch(SERVER + '/api/kt/brief', {"""

NEW = """  // Show modal with loading state immediately
  const modal = document.getElementById('kt-brief-modal');
  const content = document.getElementById('kt-brief-modal-content');
  modal.classList.add('open');

  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Generating…'; }

  // Progress ticker — updates modal and button every 3s with elapsed time + status
  const _startTs = Date.now();
  const _steps = isShort
    ? ['Reading articles…', 'Analysing key developments…', 'Drafting strategic implications…', 'Finalising brief…']
    : ['Reading 200+ articles…', 'Identifying key developments…', 'Analysing military engagement…', 'Assessing energy threats…', 'Evaluating alliance dynamics…', 'Drafting strategic implications…', 'Selecting charts…', 'Finalising brief…'];
  let _stepIdx = 0;
  const _updateProgress = () => {
    const secs = Math.round((Date.now() - _startTs) / 1000);
    const step = _steps[_stepIdx % _steps.length];
    _stepIdx++;
    content.innerHTML = `<div class="kt-loading-state" style="padding:40px 20px;text-align:center">
      <div class="spinner" style="margin:0 auto 16px"></div>
      <div style="font-size:13px;color:var(--ink-2);margin-bottom:8px">${step}</div>
      <div style="font-size:11px;color:var(--ink-3)">${secs}s elapsed · typically 60–90s for full brief</div>
    </div>`;
    if (btn) btn.innerHTML = '<span class="spinner"></span> ' + secs + 's…';
  };
  _updateProgress();
  const _ticker = setInterval(_updateProgress, 3000);

  try {
    // Step 1: Generate the text brief for display in modal
    const textResp = await fetch(SERVER + '/api/kt/brief', {"""

assert OLD in src, "Target not found"
src = src.replace(OLD, NEW, 1)

# Also clear the ticker when the brief is done or errors
OLD_CATCH = """  } catch(e) {
    modal.classList.remove('open');
    if (btn) { btn.disabled = false; btn.innerHTML = origLabel; }
    toast('Brief failed: ' + e.message);
  }
}

async function openBriefPDF"""

NEW_CATCH = """  } catch(e) {
    clearInterval(_ticker);
    modal.classList.remove('open');
    if (btn) { btn.disabled = false; btn.innerHTML = origLabel; }
    toast('Brief failed: ' + e.message);
  }
}

async function openBriefPDF"""

assert OLD_CATCH in src, "Catch target not found"
src = src.replace(OLD_CATCH, NEW_CATCH, 1)

# Clear ticker when brief text arrives (before rendering)
OLD_RENDER = """    if (btn) { btn.disabled = false; btn.innerHTML = origLabel; }

    content.innerHTML = `"""

NEW_RENDER = """    clearInterval(_ticker);
    if (btn) { btn.disabled = false; btn.innerHTML = origLabel; }

    content.innerHTML = `"""

assert OLD_RENDER in src, "Render target not found"
src = src.replace(OLD_RENDER, NEW_RENDER, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)

print("Patched OK")
