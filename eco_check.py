import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

old = ('   [_sys.executable,\n'
       '             str(BASE_DIR / "eco_scraper_sub.py"),\n'
       '             str(self.CDP_PROFILE), str(self.CDP_PORT),\n'
       '             out_file.name, ids_file.name],\n')

new = ('   [_sys.executable,\n'
       '             str(BASE_DIR / "eco_scraper_sub.py"),\n'
       '             str(self.CDP_PROFILE), str(self.CDP_PORT),\n'
       '             out_file.name, ids_file.name,\n'
       '             self.last_sync.strftime("%Y-%m-%d") if self.last_sync else ""],\n')

assert old in content, "subprocess call not found"
content = content.replace(old, new, 1)
print("Cutoff date arg added to subprocess call")

ast.parse(content)
print("Syntax OK")
with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
