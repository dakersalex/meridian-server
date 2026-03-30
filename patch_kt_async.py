import py_compile, tempfile, os

path = '/Users/alexdakers/meridian-server/server.py'
content = open(path).read()

start_idx = content.find('@app.route("/api/kt/generate", methods=["POST"])')
end_idx = content.find('@app.route("/api/kt/brief"', start_idx)

if start_idx == -1 or end_idx == -1:
    print('MARKERS NOT FOUND', start_idx, end_idx)
    exit(1)

print(f'Replacing chars {start_idx} to {end_idx}')

new_code = open('/Users/alexdakers/meridian-server/kt_new_code.txt').read()
content = content[:start_idx] + new_code + content[end_idx:]
open(path, 'w').write(content)

tmp = tempfile.mktemp(suffix='.py')
open(tmp, 'w').write(content)
try:
    py_compile.compile(tmp, doraise=True)
    print('PATCH OK - syntax clean')
except py_compile.PyCompileError as e:
    print('SYNTAX ERROR:', e)
finally:
    os.unlink(tmp)
