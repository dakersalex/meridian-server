# How Claude Works Autonomously on Meridian

## What MCP is
MCP (Model Context Protocol) is a standardised way for Claude to connect to external
resources. In your setup there are two MCP servers, both running silently in the background
— you never start or stop them manually.

---

## The Two MCP Servers

### Filesystem MCP
Gives Claude direct read/write access to ~/meridian-server/. This is how Claude edits
server.py, meridian.html, NOTES.md etc. without you pasting code into the chat.
Configured in Claude Desktop → Settings → MCP Servers.
Active automatically whenever Claude Desktop is open — you never interact with it directly.

### Claude in Chrome Extension
The extension itself is an MCP server. It exposes your browser tabs as tools Claude can
use: javascript_tool, read_console_messages, tabs_context_mcp etc.
This is the bridge that enables autonomous deploys.

---

## Why a Browser Tab is Needed

Claude runs in the cloud and can't directly reach anything on your Mac. The Chrome extension
solves this by creating a browser tab (visible as the orange-outlined ✅ Claude (MCP) tab
in Chrome) and letting Claude run JavaScript inside it. That JavaScript can reach
localhost:4242 — your local Flask server — which runs any shell command.

MCP alone can't SSH to the VPS or run git push. The shell endpoint can, because it's
subprocess.run(cmd, shell=True).

---

## The Full Chain

```
Claude
  ├── Filesystem MCP ──────────────────▶ Read/write files on Mac
  └── Claude in Chrome extension
            │
            ▼
      ✅ Claude (MCP) browser tab
            │  (JavaScript running here)
            ▼
      fetch(localhost:4242/api/dev/shell)
            │
            ▼
      Flask shell endpoint
            ├──▶ deploy.sh → git push → VPS pulls → restarts
            └──▶ ssh VPS → logs, DB queries, service restarts
```

---

## Claude Desktop vs Claude.ai in Chrome

Both work identically for autonomous operation. The Chrome extension connects to whichever
Claude interface is currently active — Desktop app or browser tab. Claude Desktop is the
main interface and autonomous deploys work throughout.

| Capability | Claude Desktop | Claude.ai in Chrome |
|---|---|---|
| Read & edit files | ✅ | ✅ |
| Run shell commands | ✅ | ✅ |
| Deploy to VPS | ✅ | ✅ |
| SSH to VPS | ✅ | ✅ |
| Check logs | ✅ | ✅ |
| Setup per session | One click (Connect) | One click (Connect) |

---

## The Three Things That Must Be True Simultaneously

1. Claude in Chrome extension is connected to the current conversation  ← only manual step
2. ✅ Claude (MCP) tab exists in Chrome — extension creates this automatically on Connect
   (don't close it — it's infrastructure, not a regular browser tab)
3. Mac Flask server running at localhost:4242 — auto-starts on Mac login via launchd,
   never needs manual action

---

## What Carries Over to a New Chat

| Thing | Transfers? | How |
|---|---|---|
| Project context | ✅ | Paste NOTES.md |
| Filesystem MCP | ✅ Auto | Always active, no action needed |
| Chrome extension | ⚠️ One click | Click Connect in extension popup |
| ✅ Claude (MCP) tab | ✅ Auto | Extension recreates it on Connect |
| Flask/shell endpoint | ✅ Auto | Already running on Mac |
| Chat history | ❌ | Not needed if NOTES.md is current |

---

## Starting a New Autonomous Session — Step by Step

### What you need open before you start
- Claude Desktop (already open — this is where you chat)
- Chrome (just needs to be running — you don't open any specific tab yourself)

### Step 1 — Copy your notes
In Terminal:
  cat ~/meridian-server/NOTES.md | pbcopy

### Step 2 — Start a new chat
Open Claude Desktop. Start a new conversation. Paste the notes.

### Step 3 — Connect the Chrome extension
Switch to Chrome. Look at the toolbar to the right of the address bar.
Find the red/orange asterisk icon — that's the Claude in Chrome extension.

  Chrome toolbar:  [M] [✳] [🧩] [A]
                        ↑
                 Click this icon

Click it. A small popup appears. Click Connect.

### Step 4 — Done
The extension automatically creates the ✅ Claude (MCP) tab group in Chrome and navigates
it to Meridian. Switch back to Claude Desktop — Claude can now run shell commands, deploy
to the VPS, and check logs, all autonomously. You don't need to touch Chrome again.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Claude can't run shell commands | Check ✅ Claude (MCP) tab exists in Chrome. If missing, tell Claude — it recreates it in one step |
| Extension not connecting | Click the asterisk icon → should show green Connected. If not, click Connect |
| Flask not responding | curl http://localhost:4242/api/health — if nothing, restart below |
| Accidentally closed the MCP tab | Tell Claude. It recreates it immediately |

Restart Flask if needed:
  launchctl unload ~/Library/LaunchAgents/com.alexdakers.meridian.plist
  launchctl load  ~/Library/LaunchAgents/com.alexdakers.meridian.plist

---

## When to Start a New Chat

Start fresh when Claude misremembers something from earlier in the session, or the
conversation has been running across many hours. NOTES.md is the real memory — not chat
history. A new chat has identical capabilities within 30 seconds of connecting.
