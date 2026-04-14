import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

old = '\ndef run_sync(source_key):'
new = '\nSCRAPERS = {"ft": FTScraper, "economist": EconomistScraper, "fa": ForeignAffairsScraper}\n\ndef run_sync(source_key):'

assert old in content, "run_sync anchor not found"
assert 'SCRAPERS = ' not in content, "SCRAPERS already defined"

content = content.replace(old, new, 1)

try:
    ast.parse(content)
    print("Syntax OK")
except SyntaxError as e:
    print("SYNTAX ERROR:", e)
    exit(1)

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
