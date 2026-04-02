import subprocess
r = subprocess.run(['grep', '-n', 'getThemeArticles', '/Users/alexdakers/meridian-server/meridian.html'], capture_output=True, text=True)
with open('/Users/alexdakers/meridian-server/tmp_getTheme.txt', 'w') as f:
    f.write(r.stdout)
print("DONE")
