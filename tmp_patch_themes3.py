with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    src = f.read()

# Patch: replace the confirm dialog and seedThemes call to mention permanent/manual themes
OLD_CONFIRM = '''  if (forceReseed) {
    if (!confirm('Reset Themes will wipe all article-theme assignments and re-analyse your entire library from scratch.\\n\\nThis takes 60-90 seconds and costs ~$0.07.\\n\\nContinue?')) return;
    await seedThemes();
    return;
  }'''

NEW_CONFIRM = '''  if (forceReseed) {
    const permNames = [...permanentThemes].filter(n =>
      (typeof ktThemes !== 'undefined' && ktThemes && ktThemes.some(t => t.name === n)) ||
      manualThemes.some(m => m && m.name === n)
    );
    const manNames = manualThemes.filter(Boolean).map(m => m.name);
    let msg = 'Reset Themes will re-analyse your library and generate 8 new themes.\\n\\nThis takes ~2 minutes and costs ~$0.07.';
    if (permNames.length) msg += '\\n\\n★ Permanent themes will be preserved: ' + permNames.join(', ');
    if (manNames.length) msg += '\\n\\n✎ Manual themes are stored locally and will remain in their slots.';
    msg += '\\n\\nThemes without ★ will be freely regenerated.\\n\\nContinue?';
    if (!confirm(msg)) return;
    await seedThemes();
    return;
  }'''

results = []
if OLD_CONFIRM in src:
    src = src.replace(OLD_CONFIRM, NEW_CONFIRM)
    results.append("confirm patch: OK")
else:
    results.append("confirm patch: FAILED")

# Patch: update seedThemes seed prompt to include "10 articles without kt-generate-sub ref to 10"
# The showSeedPrompt still says "10 dominant intelligence themes" — fix to 8
OLD_SEED_SUB = '"Meridian will analyse your ${n} articles and identify 10 dominant intelligence themes.<br>Runs once — themes update incrementally after each sync."'
NEW_SEED_SUB = '"Meridian will analyse your ${n} articles and identify 8 dominant intelligence themes, ranked by article volume.<br>Runs once — themes update incrementally after each sync."'
if OLD_SEED_SUB in src:
    src = src.replace(OLD_SEED_SUB, NEW_SEED_SUB)
    results.append("seed sub text patch: OK")
else:
    results.append("seed sub text patch: FAILED (may already be correct)")

# Patch: update seedThemes progress text "Analysing N articles with Claude Sonnet"
OLD_SEED_PROGRESS = '"Analysing ${(articles || []).length} articles with Claude Sonnet…"'
NEW_SEED_PROGRESS = '"Identifying 8 themes from ${(articles || []).length} articles with Claude Sonnet…"'
if OLD_SEED_PROGRESS in src:
    src = src.replace(OLD_SEED_PROGRESS, NEW_SEED_PROGRESS)
    results.append("seed progress text patch: OK")
else:
    results.append("seed progress text patch: FAILED (may already be correct)")

with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(src)

for r in results:
    print(r)
