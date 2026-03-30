"""
Patch meridian.html for incremental Key Themes architecture:
1. Replace generateThemes() with DB-backed loadThemes() + seed UI
2. Replace Regenerate button with Reset Themes + confirm dialog
3. Wire switchMode() to call loadThemes() from API instead of localStorage
"""
from pathlib import Path
import sys, re

p = Path('/Users/alexdakers/meridian-server/meridian.html')
src = p.read_text()
original_len = len(src)

changes = 0

# ── 1. Replace the generateThemes function (localStorage → API) ───────────────
# Find the existing generateThemes function and replace it wholesale
# with loadThemes() that reads from /api/kt/themes and handles seeding UI

OLD_GENERATE = '''async function generateThemes(force = false) {
      if (!force) {
        const cached = localStorage.getItem('meridian_themes_v1');
        if (cached) {
          try {
            const parsed = JSON.parse(cached);
            if (parsed && parsed.length === 10) {
              renderThemeGrid(parsed);
              return;
            }
          } catch(e) {}
        }
      }
      localStorage.removeItem('meridian_themes_v1');'''

if OLD_GENERATE in src:
    # Find the full function extent — replace from async function generateThemes to closing brace
    # We'll replace the whole function signature start and localStorage block
    src = src.replace(OLD_GENERATE,
'''async function generateThemes(force = false) {
      // generateThemes now delegates to loadThemes (DB-backed)
      await loadThemes(force);
    }

    async function loadThemes(forceReseed = false) {
      if (forceReseed) {
        // Show confirm dialog before wiping all tags
        if (!confirm('Reset Themes will wipe all article theme assignments and re-analyse your entire library from scratch.\\n\\nThis takes 60-90 seconds and costs ~$0.07.\\n\\nContinue?')) return;
        await seedThemes();
        return;
      }

      // Try to load from DB first
      const kt = document.getElementById('key-themes-content');
      try {
        const resp = await fetch('http://localhost:4242/api/kt/themes', {cache: 'no-store'});
        const data = await resp.json();
        if (data.seeded && data.themes && data.themes.length > 0) {
          renderThemeGrid(data.themes);
          checkEvolution();
          return;
        }
        // Not seeded yet — show seed prompt
        showSeedPrompt(kt);
      } catch(e) {
        if (kt) kt.innerHTML = '<div class="kt-error">Could not reach server: ' + e.message + '</div>';
      }
    }

    function showSeedPrompt(container) {
      if (!container) return;
      container.innerHTML = `
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;padding:60px 20px;gap:20px;text-align:center;">
          <div style="font-size:48px;">🧠</div>
          <div style="font-size:18px;font-weight:600;color:var(--ink);">Key Themes not yet generated</div>
          <div style="font-size:14px;color:var(--ink-light);max-width:400px;line-height:1.6;">
            Meridian will analyse your ${allArticles.length} articles and identify 10 dominant intelligence themes.
            This takes ~60-90 seconds and runs once — themes update incrementally after that.
          </div>
          <button onclick="seedThemes()" style="background:rgb(196,120,58);color:#fff;border:none;padding:12px 28px;border-radius:6px;font-size:15px;font-weight:600;cursor:pointer;">
            ✦ Generate Themes
          </button>
        </div>`;
    }

    async function seedThemes() {
      const kt = document.getElementById('key-themes-content');
      if (kt) kt.innerHTML = `
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;padding:60px 20px;gap:16px;text-align:center;">
          <div style="font-size:36px;">⏳</div>
          <div id="seed-progress-msg" style="font-size:16px;font-weight:600;color:var(--ink);">Starting seed…</div>
          <div style="font-size:13px;color:var(--ink-light);">Analysing ${allArticles.length} articles with Claude Sonnet…</div>
          <div style="width:300px;height:4px;background:#e8e0d4;border-radius:2px;overflow:hidden;">
            <div id="seed-progress-bar" style="height:100%;width:10%;background:rgb(196,120,58);border-radius:2px;transition:width 2s;"></div>
          </div>
        </div>`;

      // Fire the seed job
      let jobId;
      try {
        const r = await fetch('http://localhost:4242/api/kt/seed', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});
        const j = await r.json();
        jobId = j.job_id;
      } catch(e) {
        if (kt) kt.innerHTML = '<div class="kt-error">Seed failed: ' + e.message + '</div>';
        return;
      }

      // Poll for completion
      const bar = document.getElementById('seed-progress-bar');
      const msg = document.getElementById('seed-progress-msg');
      let width = 10;
      const poll = setInterval(async () => {
        try {
          const r = await fetch('http://localhost:4242/api/kt/seed/status/' + jobId, {cache:'no-store'});
          const j = await r.json();
          if (msg) msg.textContent = j.progress || 'Working…';
          width = Math.min(width + 8, 90);
          if (bar) bar.style.width = width + '%';
          if (j.status === 'done') {
            clearInterval(poll);
            if (bar) bar.style.width = '100%';
            if (msg) msg.textContent = 'Complete! Loading themes…';
            setTimeout(() => loadThemes(false), 800);
          } else if (j.status === 'error') {
            clearInterval(poll);
            if (kt) kt.innerHTML = '<div class="kt-error">Seed error: ' + (j.error || 'unknown') + '</div>';
          }
        } catch(e) { /* retry next tick */ }
      }, 3000);
    }

    async function checkEvolution() {
      try {
        const r = await fetch('http://localhost:4242/api/kt/status', {cache:'no-store'});
        const j = await r.json();
        if (j.pending_evolution) {
          showEvolutionBanner(j.pending_evolution);
        }
      } catch(e) {}
    }

    function showEvolutionBanner(ev) {
      const existing = document.getElementById('kt-evolution-banner');
      if (existing) return;
      const banner = document.createElement('div');
      banner.id = 'kt-evolution-banner';
      banner.style.cssText = 'background:#fff8ee;border:1px solid rgb(196,120,58);border-radius:6px;padding:10px 16px;margin:0 0 16px 0;font-size:13px;display:flex;align-items:center;gap:12px;';
      banner.innerHTML = `
        <span style="font-size:16px;">💡</span>
        <span style="flex:1;color:var(--ink);">Theme update available: replace <strong>${ev.replace}</strong> (${ev.replace_count} articles) with <strong>${ev.with}</strong> (${ev.with_count} articles)</span>
        <button onclick="applyEvolution()" style="background:rgb(196,120,58);color:#fff;border:none;padding:5px 12px;border-radius:4px;font-size:12px;cursor:pointer;">Apply</button>
        <button onclick="document.getElementById('kt-evolution-banner').remove()" style="background:none;border:none;color:#999;font-size:16px;cursor:pointer;">✕</button>`;
      const kt = document.getElementById('key-themes-content');
      if (kt) kt.prepend(banner);
    }

    async function applyEvolution() {
      // For now, trigger a full re-seed — future: surgical theme swap
      if (confirm('Apply theme update? This will run a full re-seed (~60s).')) {
        await seedThemes();
      }
    }

    async function _OLD_generateThemes_unused(force = false) {
      // kept for reference only — no longer called
      if (!force) {''',
    1)
    changes += 1
    print('Patch 1 OK: generateThemes replaced with loadThemes/seedThemes')
else:
    print('Patch 1 SKIP: OLD_GENERATE not found — checking for alternate form')
    # Try to find it differently
    idx = src.find('generateThemes')
    if idx >= 0:
        print('  generateThemes found at char', idx)
        print(repr(src[idx:idx+300]))

# ── 2. Replace "Regenerate" button text with "Reset Themes" ──────────────────
regen_variants = [
    ('onclick="generateThemes(true)"', 'onclick="generateThemes(true)"'),  # keep onclick, change label below
]

# Replace button label text
for old_label in ['↺ Regenerate', 'Regenerate', '↺ Reset']:
    if old_label in src:
        # Only replace if it's near generateThemes
        idx = src.find(old_label)
        while idx >= 0:
            context = src[max(0,idx-200):idx+200]
            if 'generateThemes' in context or 'Themes' in context.lower():
                src = src[:idx] + '↺ Reset Themes' + src[idx+len(old_label):]
                changes += 1
                print(f'Patch 2 OK: replaced "{old_label}" with "↺ Reset Themes"')
                break
            idx = src.find(old_label, idx+1)

# ── 3. Wire renderKeyThemes / switchMode to call loadThemes instead of generateThemes ──
# In switchMode, when switching to 'themes', it calls generateThemes()
# We want it to call loadThemes() instead (no force)
old_switch = "generateThemes();"
if old_switch in src:
    # Only replace the one in switchMode context (not force=true calls)
    # Replace all non-forced calls
    count = src.count("generateThemes();")
    src = src.replace("generateThemes();", "loadThemes();")
    changes += 1
    print(f'Patch 3 OK: replaced {count}x generateThemes() with loadThemes()')

# ── 4. Remove localStorage theme caching from renderThemeGrid / anywhere it's set ──
ls_set = "localStorage.setItem('meridian_themes_v1'"
ls_get = "localStorage.getItem('meridian_themes_v1')"
ls_rm  = "localStorage.removeItem('meridian_themes_v1')"

for ls_call in [ls_set, ls_get, ls_rm]:
    if ls_call in src:
        # Comment out rather than delete, to be safe
        src = src.replace(ls_call, '/* KT localStorage removed: ' + ls_call + ' */')
        changes += 1
        print(f'Patch 4 OK: commented out {ls_call[:50]}')

p.write_text(src)
print(f'\nTotal changes: {changes}')
print(f'Written {len(src)} chars (was {original_len})')

# Syntax check (just check it's valid HTML by looking for obvious breakage)
if '</html>' in src:
    print('HTML structure: OK (</html> present)')
else:
    print('WARNING: </html> not found')
