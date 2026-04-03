
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

results = []

# 1. Remove the logo div from the HTML
old_logo_html = '''  <div id="folder-switcher-logo">Meri<span>dian</span></div>
  <button class="folder-tab folder-tab-newsfeed active"'''

new_logo_html = '''  <button class="folder-tab folder-tab-newsfeed active"'''

if old_logo_html in html:
    html = html.replace(old_logo_html, new_logo_html)
    results.append('Logo HTML removed: OK')
else:
    results.append('Logo HTML: NOT FOUND')

# 2. Remove the logo CSS block
old_logo_css = '''#folder-switcher-logo {
  font-size: 15px;
  font-weight: 500;
  letter-spacing: -0.3px;
  color: var(--accent);
  padding-right: 20px;
  margin-right: 6px;
  border-right: 1px solid var(--rule);
  line-height: 1;
}
#folder-switcher-logo span { color: var(--ink); }
'''

if old_logo_css in html:
    html = html.replace(old_logo_css, '')
    results.append('Logo CSS removed: OK')
else:
    results.append('Logo CSS: NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\n'.join(results))
