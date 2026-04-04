with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    html = f.read()

original_len = len(html)

# ── 1. Remove the duplicate #info-strip (flex-direction:row version) ──
DUPE_OPEN = '<div id="info-strip" style="display:none;flex-direction:row;align-items:flex-start;gap:0;padding:14px 24px;background:var(--paper);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap;overflow-x:auto;position:sticky;top:184px;z-index:51;isolation:isolate;scrollbar-width:none;">'
assert html.count(DUPE_OPEN) == 1, "dupe open count != 1"

dupe_start = html.index(DUPE_OPEN)
segment = html[dupe_start:]
depth = 0
i = 0
end_idx = None
while i < len(segment):
    if segment[i:i+4] == '<div':
        depth += 1
        i += 4
    elif segment[i:i+6] == '</div>':
        depth -= 1
        if depth == 0:
            end_idx = dupe_start + i + 6
            break
        i += 6
    else:
        i += 1

assert end_idx, "Could not find closing </div> of dupe strip"
print("✓ Found dupe strip, %d chars" % (end_idx - dupe_start))

comment = '\n<!-- filter row — visually distinct from info strip above -->'
if html[dupe_start - len(comment):dupe_start] == comment:
    dupe_start -= len(comment)
    print("✓ Also removing preceding comment")

html = html[:dupe_start] + html[end_idx:]
print("✓ Removed duplicate info-strip")

# ── 2. Fix real info-strip: position:sticky → position:relative ──
REAL_OPEN_OLD = '<div id="info-strip" style="display:none;flex-direction:column;background:var(--paper);border-bottom:3px solid var(--ink);font-size:11px;position:sticky;top:184px;z-index:51;isolation:isolate;">'
REAL_OPEN_NEW = '<div id="info-strip" style="display:none;flex-direction:column;background:var(--paper);border-bottom:3px solid var(--ink);font-size:11px;position:relative;z-index:51;isolation:isolate;">'
assert html.count(REAL_OPEN_OLD) == 1, "real strip not found"
html = html.replace(REAL_OPEN_OLD, REAL_OPEN_NEW)
print("✓ Changed info-strip position:sticky → position:relative")

# ── Sanity checks ──
assert html.count('<html lang') == 1, "Duplicate <html lang!"
strip_count = html.count('id="info-strip"')
assert strip_count == 1, "info-strip count = %d" % strip_count
assert 'id="select-all-btn"' not in html, "select-all-btn still present!"
assert 'id="delete-selected-btn"' not in html, "delete-selected-btn still present!"
print("✓ All sanity checks passed")

with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(html)

print("✓ Written. %d → %d chars" % (original_len, len(html)))
