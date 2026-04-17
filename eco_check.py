import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

# Remove the early gate entirely — it's too aggressive and breaks re-runs
# The per-edition gate inside the scoring loop is sufficient
old_gate = (
    '    # ── Early gate: skip Chrome launch if latest edition already scored ──────\n'
    '    # We store the last scored edition URL in kt_meta after each successful run.\n'
    '    # If it exists and its gate key is set, the new edition hasn\'t dropped yet.\n'
    '    with sqlite3.connect(DB_PATH) as _gx:\n'
    '        _gx.execute("CREATE TABLE IF NOT EXISTS kt_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")\n'
    '        _last_ed = _gx.execute("SELECT value FROM kt_meta WHERE key=\'eco_weekly_last_edition\'").fetchone()\n'
    '    if _last_ed:\n'
    '        _last_ed_url = _last_ed[0]\n'
    '        _m = _re.search(r\'weeklyedition/([0-9-]+)\', _last_ed_url)\n'
    '        _last_ed_str = _m.group(1) if _m else ""\n'
    '        _last_gate = f"ai_pick_economist_weekly_{_last_ed_str}"\n'
    '        with sqlite3.connect(DB_PATH) as _gx:\n'
    '            _already_done = _gx.execute("SELECT value FROM kt_meta WHERE key=?", (_last_gate,)).fetchone()\n'
    '        if _already_done:\n'
    '            log.info(f"Economist weekly: last edition {_last_ed_str} already scored — skipping (no Chrome launch)")\n'
    '            return [], []\n'
    '\n'
    '    # ── CDP scrape subprocess ─────────────────────────────────────────────────\n'
)
new_gate = '    # ── CDP scrape subprocess ─────────────────────────────────────────────────\n'

assert old_gate in content, "Early gate pattern not found"
content = content.replace(old_gate, new_gate, 1)
print("Early gate removed")

ast.parse(content)
print("Syntax OK")
with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
