with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    html = f.read()

original_len = len(html)

# ── Sanity checks ──
assert html.count('<html lang') == 1, "Duplicate <html lang!"
strip_count = html.count('id="info-strip"')
assert strip_count == 1, "info-strip count = %d" % strip_count
print("✓ All sanity checks passed")
print("✓ info-strip: position:relative in file: %s" % ('position:relative' in html))
print("✓ dupe (flex-direction:row) gone: %s" % ('flex-direction:row;align-items:flex-start;gap:0;padding:14px 24px' not in html))
print("✓ select-all-btn (HTML) still present (intentional — CSS hides, JS refs it): %s" % ('id="select-all-btn"' in html))
print("Length: %d" % len(html))
