# Agent OS Dashboard — Architecture Reference

The production Agent OS dashboard at `C:\Users\valte\agent-os` (v2.5).

## Project Layout

```
src/app/
├── globals.css                    # Tailwind v4 import + glassmorphism CSS
├── layout.tsx                     # Minimal root layout
├── page.tsx                       # Main dashboard (all tabs + logic)
└── api/
    ├── chat/route.ts              # POST — send message to Hermes API
    ├── notes/route.ts             # GET — list vault notes / read note content
    └── hermes/
        ├── status/route.ts        # GET — Hermes version, gateway, MCP status
        ├── mcp/route.ts           # GET — MCP server list with status
        └── gateway/route.ts       # POST — start/stop/restart gateway
```

## Key Design Decisions

- **All-in-one page.tsx**: Dashboard is a single large component with tab switching via `activeTab` state. No separate page routes per tab.
- **Server-side API routes**: All Hermes CLI calls happen server-side via `execSync` in API routes. Client only fetches JSON.
- **No `[id]` route params on same path as parent POST**: Next.js type system rejects this. Use separate path segments or action-in-body pattern.
- **Obsidian vault**: `C:\Users\valte\Documents\Obsidian-Vault` — set via `hermes config set env.OBSIDIAN_VAULT_PATH`

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/hermes/status` | GET | Version, model, gateway status, MCP counts |
| `/api/hermes/mcp` | GET | All MCP servers with connection status |
| `/api/hermes/gateway` | POST | `{ action: "start"\|"stop"\|"restart" }` |
| `/api/notes` | GET | List vault notes (excludes `.obsidian/` folder) |
| `/api/notes?type=content&path=<path>` | GET | Read single note content |
| `/api/chat` | POST | `{ message: "..." }` → forwards to Hermes API on port 8642 |

## Serving

**CRITICAL: Port 3000 is occupied by the WhatsApp bridge (Baileys) on this machine. Agent OS MUST use a different port (3001).** Always check port availability before starting.

```bash
# Build
npm run build

# Serve (production) — use port 3001, NOT 3000
npx next start -p 3001

# Verify it's actually serving (not the WhatsApp bridge)
curl -s http://localhost:3001/ | head -5
# Should return HTML with <title>Agent OS</title>, NOT "Cannot GET /"
```

**If you get "Cannot GET /"**: The wrong process is on that port. Check with `netstat -ano | findstr ":3001"` and verify the PID is the Node.js next server, not the WhatsApp bridge.

## Windows Shortcuts (Full Pattern)

For a local web app to be accessible like a desktop app:

```powershell
# 1. Desktop shortcut (.url file)
# Create: C:\Users\<user>\Desktop\<App Name>.url
# Content:
# [InternetShortcut]
# URL=http://localhost:3001

# 2. Start Menu shortcut (.lnk)
$WshShell = New-Object -ComObject WScript.Shell
$Programs = [Environment]::GetFolderPath('StartMenu') + '\Programs'
$Shortcut = $WshShell.CreateShortcut((Join-Path $Programs '<App Name>.lnk'))
$Shortcut.TargetPath = 'http://localhost:3001'
$Shortcut.Description = '<App Description>'
$Shortcut.WorkingDirectory = '<app-dir>'
$Shortcut.Save()

# 3. Auto-start on boot (.cmd in Startup folder)
# Create: C:\Users\<user>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\<App>.cmd
# Content:
# @echo off
# cd /d <app-dir>
# start /min "" "C:\Program Files\nodejs\npx.cmd" next start -p 3001
```

## Auto-Start via Startup Folder

Create `C:\Users\<user>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\Agent_OS.cmd`:
```cmd
@echo off
cd /d C:\Users\<user>\agent-os
start /min "" "C:\Program Files\nodejs\npx.cmd" next start -p 3001
```

## Obsidian Integration

- Notes API reads `.md` files from vault, excludes `.obsidian/` config folder
- Memory Vault tab shows: vault info, searchable file list, note preview, "Open in Obsidian" deep link button
- Deep link: `obsidian://open?vault=Obsidian-Vault`
