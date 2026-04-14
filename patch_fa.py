import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()
    lines = content.split('\n')

with open('/Users/alexdakers/meridian-server/new_fa_scraper.txt', 'r') as f:
    new_scraper = f.read()

# Find exact old class boundaries
old_start = content.find('\nclass ForeignAffairsScraper:')
assert old_start != -1, "ForeignAffairsScraper not found"

old_end = content.find('\ndef run_sync(source_key):', old_start)
assert old_end != -1, "run_sync not found after FA scraper"

old_block = content[old_start:old_end]
print("Old block: %d chars, starts with: %r" % (len(old_block), old_block[:60]))
print("New block: %d chars" % len(new_scraper))

new_content = content[:old_start] + '\n' + new_scraper + content[old_end:]

# Syntax check
try:
    ast.parse(new_content)
    print("Syntax OK")
except SyntaxError as e:
    print("SYNTAX ERROR:", e)
    exit(1)

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(new_content)
print("Patched server.py")
