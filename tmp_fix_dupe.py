"""
Fix the duplicated theme_prompt block in server.py.
The patch inserted a new block but left the old incomplete block before it.
Find and remove the corrupt first fragment.
"""
from pathlib import Path

p = Path('/Users/alexdakers/meridian-server/server.py')
lines = p.read_text().splitlines(keepends=True)

# Find the first occurrence of the broken fragment (unclosed theme_prompt)
# It looks like:
#             theme_prompt = (
#                 "You are an intelligence analyst. Analyse these article titles (a representative sample "
#                 "from a corpus of " + str(total) + " articles) and identify exactly 10 "
#             theme_prompt = (    <-- this is where the second (correct) one starts
#
# We need to remove lines from the first `theme_prompt = (` up to (not including) the second one.

first_idx = None
second_idx = None

for i, line in enumerate(lines):
    if 'theme_prompt = (' in line:
        if first_idx is None:
            first_idx = i
        else:
            second_idx = i
            break

if first_idx is None or second_idx is None:
    print(f"ERROR: could not find both theme_prompt blocks (first={first_idx}, second={second_idx})")
    exit(1)

print(f"First (corrupt) block starts at line {first_idx + 1}")
print(f"Second (correct) block starts at line {second_idx + 1}")
print(f"Removing lines {first_idx + 1} to {second_idx} (inclusive)")

# Remove the corrupt first fragment (lines first_idx to second_idx - 1)
new_lines = lines[:first_idx] + lines[second_idx:]
p.write_text(''.join(new_lines))
print("Fixed OK")
