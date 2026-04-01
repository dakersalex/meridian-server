"""Remove # title lines from modal brief renderer."""
path = "/Users/alexdakers/meridian-server/meridian.html"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# The markdown renderer in downloadBriefPDF — add a strip for # title lines
OLD = """    // Render markdown to HTML
    let html = text
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')"""

NEW = """    // Render markdown to HTML — strip title lines (# ...) first
    let html = text
      .replace(/^# .+$/gm, '')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')"""

assert OLD in src, "Target not found"
src = src.replace(OLD, NEW, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Patched OK")
