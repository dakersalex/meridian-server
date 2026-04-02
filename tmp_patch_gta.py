with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    src = f.read()

# Fix 1: update getThemeArticles to accept theme object OR index
OLD_GTA = '''function getThemeArticles(idx) {
  if (!ktThemes || idx === null) return [];
  const kws = (ktThemes[idx].keywords || []).map(k => k.toLowerCase());'''

NEW_GTA = '''function getThemeArticles(idxOrTheme) {
  if (!ktThemes || idxOrTheme === null || idxOrTheme === undefined) return [];
  // Accept either a numeric index or a theme object directly
  const theme = (typeof idxOrTheme === 'object') ? idxOrTheme : ktThemes[idxOrTheme];
  if (!theme || !theme.keywords) return [];
  const kws = (theme.keywords || []).map(k => k.toLowerCase());'''

# Fix 2: anchorReg now references kws[0] but we need to keep the rest of the function working
# The function after that line uses anchorReg and kwRegs which reference kws — those are fine
# We just need to make sure the early return for missing anchor still works
# kwRegs[0] → anchorReg is still valid since kws is now derived from theme.keywords

results = []
if OLD_GTA in src:
    src = src.replace(OLD_GTA, NEW_GTA)
    results.append("getThemeArticles fix: OK")
else:
    results.append("getThemeArticles fix: FAILED")

# Fix 3: renderThemeDetail at line 3597 calls getThemeArticles(ktSelectedIdx)
# This passes an index — fine as-is since we now handle both.
# But renderThemeGrid calls getThemeArticles(theme) — also fine now.

with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(src)

for r in results:
    print(r)
