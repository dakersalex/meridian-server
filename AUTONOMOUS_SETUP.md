# How Claude Works Autonomously on Meridian

## The Big Picture

Claude can write code, deploy it to the VPS, check logs, and fix bugs — all without you typing a single Terminal command. This works through a chain of three components working together.

---

## The Three Components

### 1. Filesystem MCP
**What it is:** A small background server on your Mac that gives Claude direct access to your files.
**What it does:** Lets Claude read and edit `server.py`, `meridian.html`, `NOTES.md` etc. without you pasting code into the chat.
**How it runs:** Automatically — it's configured in Claude Desktop and starts silently whenever Claude Desktop is open. You never interact with it directly.
**Where it's configured:** Claude Desktop → Settings → MCP Servers

### 2. Claude in Chrome Extension
**What it is:** A Chrome extension that acts as a bridge between Claude and your browser.
**What it does:** Lets Claude open browser tabs, run JavaScript in them, and read the results. This is how Claude reaches your local Mac server at `localhost:4242`.
**How it runs:** The extension is always installed in Chrome. But it needs to be **connected** to the active Claude conversation — that's the one manual step (see below).
**How you know it's active:** An orange-outlined tab group appears in Chrome labelled **✅ Claude (MCP)**. Don't close this tab — it's infrastructure.

### 3. Shell Endpoint
**What it is:** A special route in your Meridian Flask server (`localhost:4242`) that runs shell commands.
**What it does:** The escape hatch that makes everything possible — Claude runs `deploy.sh`, SSHs to the VPS, restarts services, checks logs.
**How it runs:** Automatically — Flask starts on Mac login via launchd. The endpoint only accepts connections from localhost (safe).

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
             │
             ▼
       fetch(localhost:4242/api/dev/shell)
             │
             ▼
       Flask shell endpoint
             │
             ├──▶ deploy.sh → git push → VPS pulls → service restarts
             └──▶ ssh VPS → check logs, run DB queries
```

---

## Claude Desktop vs Claude.ai in Chrome

Both work identically for autonomous operation. The Chrome extension connects to whichever Claude interface is active — Desktop app or browser tab — it makes no difference.

| Capability | Claude Desktop | Claude.ai in Chrome |
|---|---|---|
| Read & edit files (Filesystem MCP) | ✅ | ✅ |
| Run shell commands | ✅ | ✅ |
| Deploy to VPS autonomously | ✅ | ✅ |
| SSH to VPS | ✅ | ✅ |
| Check logs | ✅ | ✅ |
| Setup friction | One click (Connect) | One click (Connect) |

Use whichever interface you prefer to type in. The capability is identical.

---

## Starting a New Autonomous Session

### Step 1 — Copy your notes
In Terminal:
```bash
cat ~/meridian-server/NOTES.md | pbcopy
```

### Step 2 — Open a new chat
Either Claude Desktop or claude.ai in Chrome — your choice. Start a new chat and paste the notes.

### Step 3 — Connect the extension
Look at the Chrome toolbar (top right, next to the address bar). Find the **red/orange asterisk icon** — that's the Claude in Chrome extension.

```
Chrome toolbar:  [M] [✳] [🧩] [A]
                      ↑
               Click this icon
```

Click it. A small popup appears. Click **Connect**. This links the extension to whatever Claude conversation is currently active — Desktop or browser, whichever you're using.

### Step 4 — Done
The extension automatically creates the **✅ Claude (MCP)** tab group in Chrome. Claude navigates it to `localhost:8080/meridian.html` and can immediately run shell commands, deploy, and check logs — all autonomously.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Claude can't run shell commands | Check the ✅ Claude (MCP) tab exists in Chrome. If missing, tell Claude and it will recreate it. |
| Extension not connecting | Click the asterisk icon → should show green "Connected" dot. If not, click Connect. |
| Flask server not responding | Run: `curl http://localhost:4242/api/health` — if nothing, restart Flask (see below). |
| Accidentally closed the MCP tab | Tell Claude. It can recreate it with one tool call. |

**Restart Flask on Mac:**
```bash
launchctl unload ~/Library/LaunchAgents/com.alexdakers.meridian.plist
launchctl load ~/Library/LaunchAgents/com.alexdakers.meridian.plist
```

---

## When to Start a New Chat

Start fresh when:
- Claude seems to misremember something you discussed earlier in the session
- The conversation has been going for many hours across many topics
- You see the compacted transcript summary at the top of the chat

You won't lose anything — NOTES.md contains everything that matters. The new chat will have identical capabilities within 30 seconds of connecting.
