"""Remove title-only articles from getThemeArticles — they have no summary/body
so they contribute nothing to the brief and waste one of the 60 article slots.
"""
from pathlib import Path

p = Path('/Users/alexdakers/meridian-server/meridian.html')
src = p.read_text()

OLD = """    // Title-only articles have no summary to provide a 2nd hit — if the anchor
    // appears in the title, that's sufficient (they'll be enriched eventually)
    if (!a.summary) return anchorReg.test(title);"""

NEW = """    // Title-only articles have no summary or body — useless for brief context, exclude them
    if (!a.summary) return false;"""

assert OLD in src, "OLD not found"
src = src.replace(OLD, NEW, 1)
p.write_text(src)
print("Patched OK")
