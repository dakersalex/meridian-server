with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    html = f.read()

original_len = len(html)

# ── Remove duplicate info-strip (flex-direction:row version) ──
DUPE_OPEN = '<div id="info-strip" style="display:none;flex-direction:row;align-items:flex-start;gap:0;padding:14px 24px;background:var(--paper);border-bottom:1px solid var(--rule);font-size:11px;flex-wrap:nowrap;overflow-x:auto;position:sticky;top:184px;z-index:51;isolation:isolate;scrollbar-width:none;">'
assert html.count(DUPE_OPEN) == 1, "dupe open count != 1: %d" % html.count(DUPE_OPEN)

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

assert end_idx, "Could not find closing </div>"
print("Found dupe strip: %d chars" % (end_idx - dupe_start))

# Also eat preceding comment if present
comment = '\n<!-- filter row — visually distinct from info strip above -->'
if html[dupe_start - len(comment):dupe_start] == comment:
    dupe_start -= len(comment)
    print("Also removing preceding comment")

html = html[:dupe_start] + html[end_idx:]

# ── Fix real info-strip: position:sticky → position:relative ──
REAL_OLD = '<div id="info-strip" style="display:none;flex-direction:column;background:var(--paper);border-bottom:3px solid var(--ink);font-size:11px;position:sticky;top:184px;z-index:51;isolation:isolate;">'
REAL_NEW = '<div id="info-strip" style="display:none;flex-direction:column;background:var(--paper);border-bottom:3px solid var(--ink);font-size:11px;position:relative;z-index:51;isolation:isolate;">'
assert html.count(REAL_OLD) == 1, "real strip not found: %d" % html.count(REAL_OLD)
html = html.replace(REAL_OLD, REAL_NEW)
print("Fixed real info-strip: sticky -> relative")

# ── Sanity checks ──
assert html.count('<html lang') == 1, "FATAL: duplicate html lang"
strip_count = html.count('id="info-strip"')
assert strip_count == 1, "FATAL: strip count = %d" % strip_count
assert 'position:relative' in html
print("All checks passed. strip_count=1, position:relative OK")

with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(html)

print("Written. %d -> %d chars" % (original_len, len(html)))
