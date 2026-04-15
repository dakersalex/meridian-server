import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

old = (
    '    def _enrich_after_sync():\n'
    '        for t in threads:\n'
    '            t.join()\n'
    '        log.info("Sync all complete — running title-only enrichment")\n'
    '        enrich_title_only_articles()\n'
    '        enrich_fetched_articles()\n'
    '        # score_and_autosave_new_articles() removed — AI picks sourced from\n'
    '        # homepage scraping only, never retrospectively from saved lists.\n'
)
new = (
    '    def _enrich_after_sync():\n'
    '        for t in threads:\n'
    '            t.join()\n'
    '        log.info("Sync all complete — running title-only enrichment")\n'
    '        enrich_title_only_articles()\n'
    '        enrich_fetched_articles()\n'
    '        # score_and_autosave_new_articles() removed — AI picks sourced from\n'
    '        # homepage scraping only, never retrospectively from saved lists.\n'
    '        # Push new articles to VPS automatically after every sync\n'
    '        try:\n'
    '            import subprocess as _sp\n'
    '            _r = _sp.run(\n'
    '                ["python3", str(BASE_DIR / "vps_push.py")],\n'
    '                capture_output=True, text=True, timeout=120\n'
    '            )\n'
    '            log.info(f"Auto VPS push after sync: {_r.stdout.strip()}")\n'
    '        except Exception as _pe:\n'
    '            log.warning(f"Auto VPS push failed: {_pe}")\n'
)

assert old in content, "enrich_after_sync block not found"
content = content.replace(old, new, 1)

ast.parse(content)
print("Syntax OK")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
