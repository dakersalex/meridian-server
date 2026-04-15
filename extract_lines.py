import re

with open('/Users/alexdakers/meridian-server/NOTES.md', 'r') as f:
    content = f.read()

old = '''## Mac Flask
- Restart (clean, avoids shell bridge dying): 
  `nohup bash -c "sleep 1 && kill $(lsof -ti tcp:4242) && sleep 2 && python3 ~/meridian-server/server.py" > /dev/null 2>&1 &`
- CRITICAL: restart after every deploy
- launchd throttles after repeated kills — if stuck, run `python3 ~/meridian-server/server.py &` directly in Terminal
- computer tool (Chrome MCP) cannot switch apps or open Terminal — must use shell bridge or Terminal manually'''

new = '''## Mac Flask
- **Clean restart (preferred):** `POST /api/dev/restart` — Flask spawns new process and exits cleanly, shell bridge survives
  ```js
  fetch('http://localhost:4242/api/dev/restart', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'})
  ```
- **Fallback if Flask is down:** `nohup bash -c "sleep 0.5 && lsof -ti tcp:4242 | xargs kill -9 2>/dev/null && sleep 2 && python3 ~/meridian-server/server.py" > /dev/null 2>&1 &`
  Fire-and-forget (no await) so shell bridge survives long enough
- **Last resort:** `python3 ~/meridian-server/server.py &` directly in Terminal
- CRITICAL: restart after every deploy
- launchd throttles after repeated kills in quick succession — use /api/dev/restart to avoid this
- computer tool (Chrome MCP) is scoped to browser viewport — cannot switch to Terminal or other apps'''

assert old in content, "Pattern not found"
content = content.replace(old, new, 1)

with open('/Users/alexdakers/meridian-server/NOTES.md', 'w') as f:
    f.write(content)
print("Done")
