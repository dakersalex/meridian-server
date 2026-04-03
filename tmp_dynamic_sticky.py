
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

# Add a JS function that measures row heights and sets sticky tops dynamically
# Insert just before the closing </script> tag at end of file
old_last = "loadAll();checkServer().then(async()=>{await loadFromServer();await loadInterviews();await loadSuggestedCount();});setInterval(checkServer,30000);window.scrollTo(0,0);"

new_last = """function recalcStickyTops() {
  const masthead = document.querySelector('.masthead');
  const fs = document.getElementById('folder-switcher');
  const mn = document.getElementById('main-nav');
  const is_ = document.getElementById('info-strip');
  const fh = document.getElementById('feed-header-outer');
  if (!masthead || !fs || !mn) return;
  const h0 = masthead.offsetHeight;
  const h1 = fs.offsetHeight;
  const h2 = mn.offsetHeight;
  const h3 = is_ ? is_.offsetHeight : 0;
  fs.style.top = h0 + 'px';
  mn.style.top = (h0 + h1) + 'px';
  if (is_) is_.style.top = (h0 + h1 + h2) + 'px';
  if (fh) fh.style.top = (h0 + h1 + h2 + h3) + 'px';
}
recalcStickyTops();
window.addEventListener('resize', recalcStickyTops);
loadAll();checkServer().then(async()=>{await loadFromServer();await loadInterviews();await loadSuggestedCount();});setInterval(checkServer,30000);window.scrollTo(0,0);"""

if old_last in html:
    html = html.replace(old_last, new_last)
    print('Dynamic sticky tops JS: OK')
else:
    print('NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)
