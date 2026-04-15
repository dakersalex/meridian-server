import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

# Find the dev/shell endpoint to anchor near it
anchor = '@app.route("/api/dev/shell"'
assert anchor in content, "anchor not found"

new_endpoint = '''
@app.route("/api/dev/restart", methods=["POST"])
def dev_restart():
    """Restart Flask by spawning a new process then exiting.
    The shell bridge survives long enough to return the response before the old process dies."""
    import subprocess, sys, os, time, threading
    def _restart():
        time.sleep(0.5)
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__)],
            stdout=open(os.path.join(BASE_DIR, "meridian.log"), "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
            cwd=str(BASE_DIR)
        )
        os._exit(0)
    threading.Thread(target=_restart, daemon=True).start()
    return jsonify({"ok": True, "message": "Restarting..."})

'''

content = content.replace(anchor, new_endpoint + anchor, 1)

ast.parse(content)
print("Syntax OK")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
