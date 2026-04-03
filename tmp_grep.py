import subprocess, os

# List extension files
r = subprocess.run(['find', '/Users/alexdakers/meridian-server/extension', '-type', 'f'], capture_output=True, text=True)

# Check manifest for BBG/Bloomberg references
r2 = subprocess.run(['grep', '-ri', 'bloomberg\|BBG\|scraper\|saved\|watchlist', 
                     '/Users/alexdakers/meridian-server/extension/'], capture_output=True, text=True)

with open('/Users/alexdakers/meridian-server/tmp_ext.txt', 'w') as f:
    f.write("=== Extension files ===\n" + r.stdout)
    f.write("\n=== Bloomberg/scraper refs ===\n" + r2.stdout[:3000])
print("DONE")
