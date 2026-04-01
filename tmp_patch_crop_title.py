"""patch: update _find_top_crop and _extract_figure_title in brief_pdf.py"""
from pathlib import Path

p = Path('/Users/alexdakers/meridian-server/brief_pdf.py')
src = p.read_text()

# Fix 1: extend scan ceiling and lower brightness threshold
OLD1 = """    w, h = img.size
    TITLE_REGION_END = min(95, h // 4)  # title block never beyond 95px

    last_dark_y = 0
    for y in range(6, TITLE_REGION_END):
        px = _sample_row(img, y)
        if _row_dark_count(px) >= 2:
            last_dark_y = y

    if last_dark_y == 0:
        return 0  # no title text found

    return last_dark_y + 2"""

NEW1 = """    w, h = img.size
    # Scan to y=110: some 3-line subtitle blocks extend to y=83+
    # Use threshold 155 (not 130) to catch medium-grey italic subtitle text
    TITLE_REGION_END = min(110, h // 4)

    last_dark_y = 0
    for y in range(6, TITLE_REGION_END):
        px = _sample_row(img, y)
        if sum(1 for p in px if max(p) < 155) >= 2:
            last_dark_y = y

    if last_dark_y == 0:
        return 0

    return last_dark_y + 2"""

assert OLD1 in src, f"OLD1 not found"
src = src.replace(OLD1, NEW1, 1)
print("fix1: OK")

# Fix 2: improve figure title extraction - don't strip the whole desc on first comma
# The issue is descriptions like "Brent crude oil prices in 2026, $ per barrel"
# get stripped to just "Brent crude oil prices in 2026" which is good,
# but "The chart shows..." gets stripped to "The chart" which is bad.
# Fix: if title starts with "The chart" or is very short, use more of the description
OLD2 = """def _extract_figure_title(description, caption):
    \"\"\"Derive a clean short figure title from the Haiku description.\"\"\"
    desc = (description or "").strip()
    desc = re.sub(r"^#+\\s*", "", desc)
    if not desc:
        return "Map" if "map" in (caption or "").lower() else "Chart"
    for sep in [",", ".", ";"]:
        if sep in desc:
            title = desc.split(sep)[0].strip()
            break
    else:
        title = desc
    title = re.sub(
        r"\\s+(surged?|fell|drops?|rose|declined?|increased?|decreased?|"
        r"shows?|reveals?|indicates?|demonstrates?|peaked?|spiked?)\\b.*",
        "", title, flags=re.IGNORECASE)
    if len(title) > 70:
        title = title[:70].rsplit(" ", 1)[0]
    return title.rstrip(".,;") if title else "Figure"
"""

NEW2 = """def _extract_figure_title(description, caption):
    \"\"\"Derive a clean short figure title from the Haiku description.\"\"\"
    desc = (description or "").strip()
    desc = re.sub(r"^#+\\s*", "", desc)
    if not desc:
        return "Map" if "map" in (caption or "").lower() else "Chart"

    # Strip generic openers like "The chart shows..." to get to the subject
    desc = re.sub(r"^(The chart|This chart|The graph|This graph|The map|This map)"
                  r"\\s+(shows?|depicts?|displays?|illustrates?|indicates?)\\s+",
                  "", desc, flags=re.IGNORECASE)

    # Take first clause up to comma or period
    for sep in [",", ".", ";"]:
        if sep in desc:
            title = desc.split(sep)[0].strip()
            break
    else:
        title = desc

    # Strip trailing interpretive verb phrases
    title = re.sub(
        r"\\s+(surged?|fell|drops?|rose|declined?|increased?|decreased?|"
        r"shows?|reveals?|indicates?|demonstrates?|peaked?|spiked?|has\\s)\\b.*",
        "", title, flags=re.IGNORECASE)

    # If still too generic, use first 2 clauses
    if len(title) < 10 or title.lower() in ("the chart", "the graph", "the map"):
        parts = re.split(r"[,.]", desc)
        title = " — ".join(p.strip() for p in parts[:2] if p.strip())

    if len(title) > 72:
        title = title[:72].rsplit(" ", 1)[0]
    return title.rstrip(".,;") if title else "Figure"
"""

assert OLD2 in src, f"OLD2 not found"
src = src.replace(OLD2, NEW2, 1)
print("fix2: OK")

p.write_text(src)
print("Written OK")
