"""Fix downloadBriefPDF: replace window.open (blocked as popup) with window.location.href (navigates current tab, triggers download cleanly)."""
path = "/Users/alexdakers/meridian-server/meridian.html"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

old = "    // Trigger download — window.open() is more reliable than hidden <a> for large files\n    window.open(SERVER + '/api/kt/brief/pdf/download/' + jobId, '_blank');"
new = "    // Trigger download via location.href — avoids Chrome popup blocker\n    // Content-Disposition: attachment means the file downloads without navigating away\n    window.location.href = SERVER + '/api/kt/brief/pdf/download/' + jobId;"

assert old in src, "Target string not found"
src = src.replace(old, new, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Patched OK")
