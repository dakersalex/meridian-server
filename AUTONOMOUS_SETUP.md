# How Claude Works Autonomously on Meridian

## Why the browser tab matters

Claude runs in the cloud and can't directly reach anything on your Mac. The Chrome extension
solves this: it creates a browser tab (the orange-outlined ✅ Claude (MCP) tab in Chrome) and
lets Claude run JavaScript inside it. That JavaScript can reach localhost:4242 — your local
Flask server — which then executes any shell command. That's the bridge.

---

## The Three Components

### 1. Filesystem MCP
Gives Claude direct read/write access to ~/meridian-server/ — so it can edit server.py,
meridian.html, NOTES.md etc. without you pasting code into the chat.
Runs automatically in the background. Configured in Claude Desktop → Settings → MCP Servers.
You never interact with it directly.

### 2. Claude in Chrome Extension
The bridge between Claude and your Mac. Creates a browser tab (✅ Claude (MCP)) and lets
Claude run JavaScript in it to reach localhost:4242.
Always installed in Chrome, but needs to be connected to each new conversation — that's
the one manual step per session.
The ✅ Claude (MCP) tab it creates is infrastructure — don't close it.

### 3. Shell Endpoint
A route in your Meridian Flask server (localhost:4242/api/dev/shell) that executes shell
commands. Only accepts connections from localhost so it's safe.
Runs automatically — Flask starts on Mac login via launchd.
This is what makes deploys possible: Claude calls it to run deploy.sh, SSH to the VPS,
check logs, query the database, etc.

---

## How They Chain Together

```
Claude (Desktop app OR claude.ai in Chrome — both work identically)
  │
  ├─── Filesystem MCP ──────────────────▶ Read/write files on Mac
  │
  └─── Claude in Chrome extension
             │
             ▼
       ✅ Claude (MCP) browser tab
             │   (JavaScript running here)
             ▼
       fetch(localhost:4242/api/dev/shell)
             │
             ▼
       Flask shell endpoint
             │
             ├──▶ deploy.sh → git push → VPS pulls → service restarts
             └──▶ ssh VPS → check logs, run DB queries, restart services
```

---

## Claude Desktop vs Claude.ai in Chrome

Both work identically. The Chrome extension connects to whichever Claude interface is
currently active — Desktop app or browser tab. You've been using Claude Desktop throughout
and autonomous deploys have worked fine the whole time.

| Capability | Claude Desktop | Claude.ai in Chrome |
|---|---|---|
| Read & edit files | ✅ | ✅ |
| Run shell commands | ✅ | ✅ |
| Deploy to VPS | ✅ | ✅ |
| SSH to VPS | ✅ | ✅ |
| Check logs | ✅ | ✅ |
| Setup per session | One click (Connect) | One click (Connect) |

Use whichever interface you prefer to type in.

---

## Starting a New Autonomous Session

The only thing that doesn't carry over to a new conversation automatically is the extension
connection (item 1 below). Everything else is already running.

**Three things that must be true simultaneously:**
1. Claude in Chrome extension is connected to the current conversation ← only manual step
2. ✅ Claude (MCP) tab exists in Chrome (extension creates this automatically on Connect)
3. Mac Flask server is running at localhost:4242 (auto-starts on login)

**Steps:**
```
1.  cat ~/meridian-server/NOTES.md | pbcopy  →  paste into new chat
2.  Click the red/orange asterisk icon in the Chrome toolbar (right of address bar)
3.  Click Connect in the popup
4.  Done
```

The ✅ Claude (MCP) tab reappears automatically. Claude navigates it to Meridian and can
immediately run shell commands, deploy, and check logs.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Claude can't run shell commands | Check ✅ Claude (MCP) tab exists in Chrome. If missing, tell Claude — it recreates it in one step. |
| Extension not connecting | Click the asterisk icon → should show green Connected. If not, click Connect. |
| Flask not responding | Run: curl http://localhost:4242/api/health |
| Accidentally closed the MCP tab | Just tell Claude. It will recreate it immediately. |

**Restart Flask if needed:**
```bash
launchctl unload ~/Library/LaunchAgents/com.alexdakers.meridian.plist
launchctl load  ~/Library/LaunchAgents/com.alexdakers.meridian.plist
```

---

## When to Start a New Chat

Start fresh when Claude starts misremembering things or the conversation has been running
across many hours and topics. You won't lose anything — NOTES.md is the real memory, not
the chat history. A new chat has identical capabilities within 30 seconds of connecting.
