import subprocess
r1 = subprocess.run(['sed', '-n', '377,430p', '/Users/alexdakers/meridian-server/meridian.html'], capture_output=True, text=True)
r2 = subprocess.run(['sed', '-n', '3184,3220p', '/Users/alexdakers/meridian-server/meridian.html'], capture_output=True, text=True)
r3 = subprocess.run(['sed', '-n', '3580,3600p', '/Users/alexdakers/meridian-server/meridian.html'], capture_output=True, text=True)
with open('/Users/alexdakers/meridian-server/tmp_scan.txt', 'w') as f:
    f.write("=== FOLDER CSS ===\n" + r1.stdout)
    f.write("\n=== switchMode ===\n" + r2.stdout)
    f.write("\n=== init area ===\n" + r3.stdout)
print("DONE")
