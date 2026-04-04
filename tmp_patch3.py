with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    html = f.read()

original_len = len(html)
errors = []

# ── 1. Remove HTML buttons from filter row ──
old_sel_btns = (
    '\n  <button class="btn btn-outline" onclick="selectAll()" style="font-size:11px;padding:4px 8px;display:none" id="select-all-btn">Select all</button>'
    '\n  <button class="btn btn-outline" onclick="deleteSelected()" style="font-size:11px;padding:4px 8px;display:none;border-color:var(--red);color:var(--red)" id="delete-selected-btn">Delete selected</button>'
)
if html.count(old_sel_btns) == 1:
    html = html.replace(old_sel_btns, '')
    print("OK 1: removed select-all + delete-selected HTML buttons")
else:
    errors.append("FAIL 1: sel-btns count = %d" % html.count(old_sel_btns))

# ── 2. Remove CSS rule for those buttons (no longer needed) ──
old_css = '  #select-all-btn, #delete-selected-btn { display: none !important; }\n'
if html.count(old_css) == 1:
    html = html.replace(old_css, '')
    print("OK 2: removed CSS hide rule")
else:
    errors.append("FAIL 2: css rule count = %d" % html.count(old_css))

# ── 3. Null-guard JS: selectAll() — two getElementById calls ──
old_select_all_fn = (
    "  document.getElementById('delete-selected-btn').style.display='';\n"
    "  document.getElementById('select-all-btn').textContent='Deselect all ('+selectedIds.size+')';"
)
new_select_all_fn = (
    "  const _dsbtn=document.getElementById('delete-selected-btn'); if(_dsbtn)_dsbtn.style.display='';\n"
    "  const _sabtn=document.getElementById('select-all-btn'); if(_sabtn)_sabtn.textContent='Deselect all ('+selectedIds.size+')';"
)
if html.count(old_select_all_fn) == 1:
    html = html.replace(old_select_all_fn, new_select_all_fn)
    print("OK 3: null-guarded selectAll() getElementById calls")
else:
    errors.append("FAIL 3: selectAll ids count = %d" % html.count(old_select_all_fn))

# ── 4. Null-guard JS: deleteSelected() — two getElementById calls in the Promise chain ──
old_del_chain = (
    "document.getElementById('delete-selected-btn').style.display='none';"
    "document.getElementById('select-all-btn').textContent='Select all';"
)
new_del_chain = (
    "const _dsb=document.getElementById('delete-selected-btn');if(_dsb)_dsb.style.display='none';"
    "const _sab=document.getElementById('select-all-btn');if(_sab)_sab.textContent='Select all';"
)
if html.count(old_del_chain) == 1:
    html = html.replace(old_del_chain, new_del_chain)
    print("OK 4: null-guarded deleteSelected() getElementById calls")
else:
    errors.append("FAIL 4: deleteSelected ids count = %d" % html.count(old_del_chain))

# ── Sanity checks ──
assert html.count('<html lang') == 1, "FATAL: duplicate <html lang"
strip_count = html.count('id="info-strip"')
assert strip_count == 1, "FATAL: info-strip count = %d" % strip_count
assert 'position:relative' in html, "FATAL: info-strip not position:relative"
assert 'flex-direction:row;align-items:flex-start;gap:0;padding:14px 24px' not in html, "FATAL: dupe strip still present"

if errors:
    for e in errors:
        print(e)
    raise Exception("Patch had errors — not writing file")

with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(html)

print("OK: Written. %d -> %d chars" % (original_len, len(html)))
print("OK: info-strip count = %d" % strip_count)
print("OK: select-all-btn in HTML = %s" % ('id="select-all-btn"' in html))
