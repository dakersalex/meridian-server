import subprocess
r = subprocess.run(['sed', '-n', '3673,3760p', '/Users/alexdakers/meridian-server/meridian.html'],
    capture_output=True, text=True)
with open('/Users/alexdakers/meridian-server/tmp_grep_out.txt', 'w') as f:
    f.write(r.stdout)
print("DONE")
