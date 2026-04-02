import subprocess
# Check lines around 4163 for any remaining literal newlines in JS strings
r = subprocess.run(['sed', '-n', '4150,4220p', '/Users/alexdakers/meridian-server/meridian.html'], capture_output=True, text=True)
with open('/Users/alexdakers/meridian-server/tmp_syntax.txt', 'w') as f:
    f.write(r.stdout)
# Also use node to check for syntax errors in extracted JS
import re
with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    content = f.read()
# Find all <script> blocks and check for raw newlines inside template literals/strings
# Quick heuristic: look for join(' followed by a literal newline before ')
issues = []
for i, line in enumerate(content.split('\n'), 1):
    # Look for strings that contain literal newlines (would be split across lines in a join/string call)
    pass
print("DONE")
