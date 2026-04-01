"""Final targeted fix: extend TITLE_REGION_END and fix title extraction edge cases"""
from pathlib import Path
import re

p = Path('/Users/alexdakers/meridian-server/brief_pdf.py')
src = p.read_text()

# Fix 1: extend ceiling from 110 to 120 (for tall charts with long title blocks)
OLD1 = "    TITLE_REGION_END = min(110, h // 4)"
NEW1 = "    TITLE_REGION_END = min(120, h // 4)"
assert OLD1 in src
src = src.replace(OLD1, NEW1, 1)
print("fix1 ceiling: OK")

# Fix 2: improve title extraction
# Problem patterns:
# - "U — S" from "U.S. average tariff..." splitting on "." in abbreviation
# - "The chart compares..." not being stripped (only shows/depicts listed)
# - "Gold prices have risen dramatically" not stripped (risen not in verb list)
# - "that stocks bought at higher CAPE" (description starts mid-sentence)

OLD2 = """    # Strip generic openers like "The chart shows..." to get to the subject
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
        title = " — ".join(p.strip() for p in parts[:2] if p.strip())"""

NEW2 = """    # Strip generic openers
    desc = re.sub(
        r"^(The chart|This chart|The graph|This graph|The map|This map)"
        r"\\s+(shows?|depicts?|displays?|illustrates?|indicates?|compares?|"
        r"reveals?|demonstrates?|presents?|tracks?|plots?)\\s+",
        "", desc, flags=re.IGNORECASE)

    # Remove interpretive trailing verb phrases before splitting
    desc_clean = re.sub(
        r"\\s+(has\\s+)?(surged?|risen|fell|drops?|rose|declined?|increased?|"
        r"decreased?|shows?|reveals?|indicates?|demonstrates?|peaked?|spiked?|"
        r"grown?|shrunk?|soared?|plunged?)\\b.*",
        "", desc, flags=re.IGNORECASE)
    if len(desc_clean) > 8:
        desc = desc_clean

    # Split on comma/semicolon first (safer than period due to abbreviations like U.S.)
    # Only split on period if it's followed by a space and capital letter (sentence end)
    for sep in [",", ";"]:
        if sep in desc:
            title = desc.split(sep)[0].strip()
            break
    else:
        # Period split: only at sentence boundaries, not abbreviations
        parts = re.split(r"\\.(?=\\s+[A-Z])", desc)
        title = parts[0].strip()

    # If still too generic or too short, take first two comma-clauses
    if len(title) < 10 or title.lower() in ("the chart", "the graph", "the map",
                                              "the", "this"):
        parts = re.split(r"[,;]", desc)
        title = ", ".join(p.strip() for p in parts[:2] if p.strip())"""

assert OLD2 in src, "OLD2 not found"
src = src.replace(OLD2, NEW2, 1)
print("fix2 title: OK")

p.write_text(src)
print("Written OK")
