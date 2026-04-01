"""Remove orphaned lines left from the partial replacement of _build_article_context."""
from pathlib import Path

p = Path('/Users/alexdakers/meridian-server/brief_pdf.py')
src = p.read_text()

# The orphan: after the correct return statement there are two garbage lines
# "---\n\n'.join(parts)\n"  which appear as separate lines
ORPHAN = "\n---\n\n'.join(parts)\n"
if ORPHAN in src:
    src = src.replace(ORPHAN, "\n", 1)
    p.write_text(src)
    print("Removed orphan OK")
else:
    # Try showing the area around line 445
    lines = src.splitlines()
    for i, l in enumerate(lines[440:455], 441):
        print(i, repr(l))
