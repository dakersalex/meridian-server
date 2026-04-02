import subprocess

# Read the relevant sections we need to patch
r1 = subprocess.run(['sed', '-n', '455,500p', '/Users/alexdakers/meridian-server/meridian.html'], capture_output=True, text=True)
r2 = subprocess.run(['sed', '-n', '2985,3040p', '/Users/alexdakers/meridian-server/meridian.html'], capture_output=True, text=True)
# Also find kt-header-title and kt-regenerate-btn lines for context
r3 = subprocess.run(['grep', '-n', 'kt-header\|kt-regenerate\|kt-card-name\|kt-card-emoji\|kt-card-count\|kt-selected-arrow\|pinnedTopics\|loadThemes', 
                     '/Users/alexdakers/meridian-server/meridian.html'], capture_output=True, text=True)

with open('/Users/alexdakers/meridian-server/tmp_grep_out.txt', 'w') as f:
    f.write("=== CSS 455-500 ===\n" + r1.stdout)
    f.write("\n=== renderThemeGrid 2985-3040 ===\n" + r2.stdout)
    f.write("\n=== KEY LINES ===\n" + r3.stdout[:3000])
print("DONE")
