import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

# Remove the live port check from sync_last_run — it's misleading
old_live = (
    '    # Also do a live port check\n'
    '    import socket as _sock\n'
    '    try:\n'
    '        s = _sock.create_connection(("localhost", 9223), timeout=1)\n'
    '        s.close()\n'
    '        result[\'eco_cdp_live\'] = True\n'
    '    except OSError:\n'
    '        result[\'eco_cdp_live\'] = False\n'
    '    return jsonify(result)'
)
new_live = (
    '    # eco_cdp_live: True if last recorded status was OK\n'
    '    cdp_status = result.get("eco_cdp_status", "")\n'
    '    result["eco_cdp_live"] = not cdp_status.startswith("DOWN")\n'
    '    return jsonify(result)'
)
assert old_live in content, "live check not found"
content = content.replace(old_live, new_live, 1)
print("Live check replaced with kt_meta status")

ast.parse(content)
print("Syntax OK")
with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
