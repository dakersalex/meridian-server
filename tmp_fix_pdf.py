"""Fix brief_pdf.py — three bugs: split re.split line, SQL insight!=, bold regex."""
path = "/Users/alexdakers/meridian-server/brief_pdf.py"

with open(path, "rb") as f:
    raw = f.read()

# Bug 3: re.split raw string has a real newline inside it.
# Line 65: b'        parts=re.split(r"'
# Line 66: b'(?=## )",text.strip()); secs=[]'
# Join them with \n replaced by the correct escape sequence.
raw = raw.replace(
    b'parts=re.split(r"\n(?=## )"',
    b'parts=re.split(r"\\n(?=## )"'
)

# Decode to str for remaining fixes
src = raw.decode("utf-8")

# Bug 1: SQL missing empty string in insight comparison
src = src.replace("AND insight!= AND", "AND insight != '' AND")

# Bug 2: Bold regex strips content — restore \1 capture group
# The broken version is: r"<b></b>"  should be: r"<b>\1</b>"
src = src.replace(
    'r"<b></b>"',
    r'r"<b>\1</b>"'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)

print("All fixes applied.")
