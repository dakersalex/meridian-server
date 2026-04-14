import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

old = 'SCRAPERS = {"ft": FTScraper, "economist": EconomistScraper, "fa": ForeignAffairsScraper}'
new = ('SCRAPERS = {"ft": FTScraper, "economist": EconomistScraper, "fa": ForeignAffairsScraper}\n'
       'sync_status = {k: {"running": False, "last_run": None, "last_error": None, "articles_found": 0, "articles_new": 0} for k in SCRAPERS}')

assert old in content, "SCRAPERS line not found"
assert 'sync_status = {' not in content, "sync_status already defined"

content = content.replace(old, new, 1)

ast.parse(content)
print("Syntax OK")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
