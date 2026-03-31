"""
Fix downloadBriefPDF() in meridian.html:
Replace the hidden <a> element download trick with window.open() which
reliably triggers Chrome's native download manager for large files.
"""
path = "/Users/alexdakers/meridian-server/meridian.html"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

OLD = """    // Trigger download
    const a = document.createElement('a');
    a.href = SERVER + '/api/kt/brief/pdf/download/' + jobId;
    a.download = `meridian_brief_${theme.name.toLowerCase().replace(/[^a-z0-9]+/g,'-')}_${type}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);"""

NEW = """    // Trigger download — window.open() is more reliable than hidden <a> for large files
    window.open(SERVER + '/api/kt/brief/pdf/download/' + jobId, '_blank');"""

assert OLD in src, "Download block not found"
src = src.replace(OLD, NEW, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Patched OK")
