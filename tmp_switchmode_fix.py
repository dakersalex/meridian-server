
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# Fix switchMode to use new .active class and info-strip id
old_switch = '''function switchMode(mode) {
  ktCurrentMode = mode;
  const newsfeedEl = document.getElementById('tab-newsfeed');
  const themesEl   = document.getElementById('tab-themes');
  const ktView     = document.getElementById('key-themes-view');
  const mainNav    = document.getElementById('main-nav');
  const tallyBar   = document.getElementById('tally-bar');
  const actBar     = document.getElementById('activity-bar');
  const feedHeader = document.getElementById('feed-header-outer');
  const mainLayout = document.querySelector('.main-layout');
  const mobileFilter = document.getElementById('mobile-filter-bar');

  const briefingEl  = document.getElementById('tab-briefing');
  const briefingView = document.getElementById('briefing-view');

  // Reset all tabs to inactive state
  newsfeedEl.classList.remove('inactive');
  themesEl.classList.remove('active');
  if (briefingEl) briefingEl.classList.remove('active');

  if (mode === 'themes') {
    newsfeedEl.classList.add('inactive');
    themesEl.classList.add('active');
    ktView.classList.add('visible');
    if (briefingView) briefingView.classList.remove('visible');
    if (mainLayout) mainLayout.style.display = 'none';
    if (feedHeader) feedHeader.style.display = 'none';
    if (tallyBar)   tallyBar.style.display = 'none';
    if (actBar)     actBar.style.display = 'none';
    if (mobileFilter) mobileFilter.style.display = 'none';
    mainNav.style.display = 'none';
    renderKeyThemes();
  } else if (mode === 'briefing') {
    newsfeedEl.classList.add('inactive');
    if (briefingEl) briefingEl.classList.add('active');
    ktView.classList.remove('visible');
    if (briefingView) briefingView.classList.add('visible');
    if (mainLayout) mainLayout.style.display = 'none';
    if (feedHeader) feedHeader.style.display = 'none';
    if (tallyBar)   tallyBar.style.display = 'none';
    if (actBar)     actBar.style.display = 'none';
    if (mobileFilter) mobileFilter.style.display = 'none';
    mainNav.style.display = 'none';
    bgInit();
  } else {
    ktView.classList.remove('visible');
    if (briefingView) briefingView.classList.remove('visible');
    if (mainLayout) mainLayout.style.display = '';
    if (feedHeader) feedHeader.style.display = '';
    if (tallyBar)   tallyBar.style.display = '';
    if (actBar)     actBar.style.display = '';'''

new_switch = '''function switchMode(mode) {
  ktCurrentMode = mode;
  const newsfeedEl = document.getElementById('tab-newsfeed');
  const themesEl   = document.getElementById('tab-themes');
  const ktView     = document.getElementById('key-themes-view');
  const mainNav    = document.getElementById('main-nav');
  const infoStrip  = document.getElementById('info-strip');
  const feedHeader = document.getElementById('feed-header-outer');
  const mainLayout = document.querySelector('.main-layout');
  const mobileFilter = document.getElementById('mobile-filter-bar');

  const briefingEl  = document.getElementById('tab-briefing');
  const briefingView = document.getElementById('briefing-view');

  // Reset all tabs — remove active from all
  [newsfeedEl, themesEl, briefingEl].forEach(el => { if (el) el.classList.remove('active'); });

  if (mode === 'themes') {
    if (themesEl) themesEl.classList.add('active');
    ktView.classList.add('visible');
    if (briefingView) briefingView.classList.remove('visible');
    if (mainLayout) mainLayout.style.display = 'none';
    if (feedHeader) feedHeader.style.display = 'none';
    if (infoStrip)  infoStrip.style.display = 'none';
    if (mobileFilter) mobileFilter.style.display = 'none';
    mainNav.style.display = 'none';
    renderKeyThemes();
  } else if (mode === 'briefing') {
    if (briefingEl) briefingEl.classList.add('active');
    ktView.classList.remove('visible');
    if (briefingView) briefingView.classList.add('visible');
    if (mainLayout) mainLayout.style.display = 'none';
    if (feedHeader) feedHeader.style.display = 'none';
    if (infoStrip)  infoStrip.style.display = 'none';
    if (mobileFilter) mobileFilter.style.display = 'none';
    mainNav.style.display = 'none';
    bgInit();
  } else {
    if (newsfeedEl) newsfeedEl.classList.add('active');
    ktView.classList.remove('visible');
    if (briefingView) briefingView.classList.remove('visible');
    if (mainLayout) mainLayout.style.display = '';
    if (feedHeader) feedHeader.style.display = '';
    if (infoStrip)  infoStrip.style.display = '';'''

if old_switch in html:
    html = html.replace(old_switch, new_switch)
    results.append('switchMode: OK')
else:
    results.append('switchMode: NOT FOUND')

# Also remove the old .folder-tab-newsfeed.inactive CSS which is no longer needed
old_inactive_css = '''.folder-tab-newsfeed.inactive {'''
if old_inactive_css in html:
    # Find the whole block and replace with comment
    idx = html.find(old_inactive_css)
    end = html.find('}', idx) + 1
    html = html[:idx] + '/* inactive state removed — using .active class instead */' + html[end:]
    results.append('inactive CSS removed: OK')
else:
    results.append('inactive CSS: not found (already clean)')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
