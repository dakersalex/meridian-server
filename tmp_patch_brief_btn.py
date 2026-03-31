"""Clean up stale kt-print-btn reference in modal close button onclick."""
path = "/Users/alexdakers/meridian-server/meridian.html"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

src = src.replace(
    "onclick=\"document.getElementById('kt-brief-modal').classList.remove('open');document.getElementById('kt-print-btn').style.display='none'\"",
    "onclick=\"document.getElementById('kt-brief-modal').classList.remove('open')\""
)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Cleanup OK")
