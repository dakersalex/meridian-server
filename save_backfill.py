import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

# ── Fix 1: Remove most-read from FA scraper ───────────────────────────────
old_scrape = (
    '                # 3. Most read\n'
    '                most_read = self._scrape_page(page, self.MOST_READ_URL, seen, "most-read")\n'
    '                articles.extend(most_read)\n'
    '                log.info("FA: most-read — %d new" % len(most_read))\n'
)
new_scrape = (
    '                # 3. Most-read handled exclusively by AI pick pipeline\n'
    '                # (avoids bypassing quality scoring gate)\n'
)
assert old_scrape in content, "FA most-read scrape block not found"
content = content.replace(old_scrape, new_scrape, 1)
print("Fix 1 (remove most-read from scraper): applied")

# ── Fix 2: Build separate set of manually-saved FA URLs for AI pick ───────
# Change _known build to track manual saves separately
old_known = (
    '    # ── Build known URLs ──────────────────────────────────────────────────────\n'
    '    with sqlite3.connect(DB_PATH) as _cx:\n'
    '        _saved = set(r[0] for r in _cx.execute("SELECT url FROM articles WHERE url!=\'\'").fetchall())\n'
    '        _suggested = set(r[0] for r in _cx.execute("SELECT url FROM suggested_articles WHERE url!=\'\'").fetchall())\n'
    '    _known = _saved | _suggested\n'
)
new_known = (
    '    # ── Build known URLs ──────────────────────────────────────────────────────\n'
    '    with sqlite3.connect(DB_PATH) as _cx:\n'
    '        # All articles (for dedup) — split by manual vs AI saved\n'
    '        _all_saved = _cx.execute("SELECT url, auto_saved FROM articles WHERE url!=\'\'").fetchall()\n'
    '        _saved = set(r[0] for r in _all_saved)  # all URLs\n'
    '        _manual_saves = set(r[0] for r in _all_saved if not r[1])  # auto_saved=0\n'
    '        _suggested = set(r[0] for r in _cx.execute("SELECT url FROM suggested_articles WHERE url!=\'\'").fetchall())\n'
    '    _known = _saved | _suggested  # used to skip already-AI-picked or suggested\n'
    '    # Manual saves are NOT in _known — they get scored but not duplicated\n'
    '    _known = _known - _manual_saves\n'
)
assert old_known in content, "known URLs block not found"
content = content.replace(old_known, new_known, 1)
print("Fix 2 (separate manual saves from _known): applied")

# ── Fix 3: In routing, skip saving if URL already manually saved ──────────
old_route_filter = (
    '        if _source not in TRUSTED_SOURCES: continue\n'
    '        if _url in _known: continue\n'
    '\n'
    '        _art_id = make_id(_source, _url)\n'
    '        log.info(f"AI pick: score={_score} [{_source}] {_title[:60]}")\n'
    '\n'
    '        if _score >= 8:\n'
    '            feed_articles.append({'
)
new_route_filter = (
    '        if _source not in TRUSTED_SOURCES: continue\n'
    '        if _url in _known: continue\n'
    '\n'
    '        _art_id = make_id(_source, _url)\n'
    '        _already_manual = _url in _manual_saves\n'
    '        log.info(f"AI pick: score={_score} [{_source}] {_title[:60]}")\n'
    '\n'
    '        if _score >= 8:\n'
    '            if _already_manual:\n'
    '                # Already saved manually — don\'t duplicate, just log\n'
    '                log.info(f"AI pick: score={_score} — already manually saved, skipping duplicate")\n'
    '                continue\n'
    '            feed_articles.append({'
)
assert old_route_filter in content, "Route filter block not found"
content = content.replace(old_route_filter, new_route_filter, 1)
print("Fix 3 (no duplicate of manual saves): applied")

ast.parse(content)
print("Syntax OK")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
