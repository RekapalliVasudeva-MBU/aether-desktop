---
name: cloudflare-tunnel-management
description: Manage Cloudflare Tunnel (cloudflared) for local server exposure with daily cron automation. Covers quick tunnels (trycloudflare.com), named tunnels (custom domain), Windows service management, daily tunnel restart, and URL extraction/reporting. Use when the user needs to expose a local server publicly via Cloudflare Tunnel.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [cloudflare, cloudflared, tunnel, quick-tunnel, named-tunnel, static-domain, cron, local-server, trycloudflare]
    category: devops
    related_skills: [devops, cronjob, web-development]
    config:
      cloudflared_path: "C:/Program Files (x86)/cloudflared/cloudflared.exe"
      project_rag_dir: "C:/Users/valte/project_rag.worktrees/ngrok-hosting-aether-minds-app"
      local_port: 8000
---

# Cloudflare Tunnel Management Skill

## When to Use
- Exposing a local server (localhost:port) to the internet via Cloudflare Tunnel (cloudflared)
- Setting up quick tunnels for temporary access (URL changes on restart) — no account needed
- Setting up named tunnels for permanent stable URLs — requires Cloudflare account + domain
- Automating daily tunnel restarts with URL extraction and reporting
- Managing Cloudflare tunnel as Windows service

## Quick Decision Guide

| Need | Use |
|------|-----|
| Temporary access, URL can change | Quick tunnel (`cloudflared tunnel --url http://localhost:8000`) |
| Permanent URL, have domain | Named tunnel + custom domain |
| Permanent URL, NO domain, free | Quick tunnel + daily cron restart (URL changes daily) |
| Production, need uptime SLA | Named tunnel + domain + health checks |

## Prerequisites
- Cloudflare account (for named tunnels)
- `cloudflared.exe` installed locally
- Local server running on target port (default 8000)
- Windows (service management) or Linux/macOS

### File Locations (2026-08-10)
- **Actual working restart script**: `C:\Users\valte\AppData\Local\hermes\skills\devops\cloudflare-tunnel-management\references\daily_tunnel_restart.py`
- **Local server (AetherMind RAG)**: `C:\Users\valte\project_rag.worktrees\ngrok-hosting-aether-minds-app\server.py` (port 8000) — runs from worktree, NOT from `C:\Users\valte\project_rag`
- **cloudflared binary**: `C:\Program Files (x86)\cloudflared\cloudflared.exe`

## How to Run

### Quick Tunnel (Temporary, Free, No Account Required)
```bash
cloudflared tunnel --url http://localhost:8000
```
- URL changes on **every restart**
- No Cloudflare account needed
- Good for temporary testing

### Named Tunnel (Permanent, Requires Domain)
1. Create tunnel in Cloudflare Dashboard → Zero Trust → Networks → Tunnels
2. `cloudflared tunnel login` (interactive browser auth)
3. `cloudflared tunnel create aether-rag`
4. `cloudflared tunnel route dns aether-rag aether-rag.yourdomain.com`
5. Install as service: `cloudflared service install <token>`
6. Configure Public Hostname in Dashboard → Routes → Add route

### Daily Auto-Restart (Quick Tunnel)
Runs at 8 AM daily, kills old tunnel, starts fresh, extracts new URL:
```bash
python C:\Users\valte\AppData\Local\hermes\skills\devops\cloudflare-tunnel-management\references\daily_tunnel_restart.py
```

## Procedure

### 1. Quick Tunnel Setup
```bash
# Start quick tunnel
cloudflared tunnel --url http://localhost:8000

# Extract URL from output (appears after "Your quick Tunnel has been created!")
# Format: https://random-words.trycloudflare.com
```

### 2. Named Tunnel Setup (Permanent)
```bash
# One-time setup (requires Cloudflare account)
cloudflared tunnel login
cloudflared tunnel create aether-rag
cloudflared tunnel route dns aether-rag aether-rag.yourdomain.com

# Get token from Dashboard → Tunnels → aether-rag → Token
cloudflared service install <token>

# In Dashboard: Routes → Add route → Subdomain: aether-rag, Domain: yourdomain.com, Service: http://localhost:8000
```

### 3. Daily Restart Cron Job
```bash
# Cron entry (runs 8 AM daily)
0 8 * * * python /path/to/daily_tunnel_restart.py
```

### 4. Windows Service Management
```powershell
# Force stop and delete stuck service
taskkill /F /IM cloudflared.exe
sc delete Cloudflared

# Install fresh with token
C:\Users\valte\cloudflared.exe service install <token>

# Verify
Get-Service Cloudflared
```

## Pitfalls

### Quick Tunnel URL Changes
- **Problem**: Quick tunnel URL changes on every restart
- **Fix**: Use named tunnel with custom domain for permanent URL, or accept daily URL change with cron job reporting

### Service Stuck in StopPending
- **Problem**: `cloudflared service install` fails with "service already installed" but service shows StopPending
- **Fix**: Must run as Administrator, use `taskkill /F /IM cloudflared.exe` then `sc delete Cloudflared` before reinstall

### Tunnel Exits Immediately
- **Problem**: Quick tunnel process exits when shell backgrounded with `&`
- **Fix**: Use `subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS` on Windows, or run in screen/tmux on Linux

### Domain Dropdown Empty in Dashboard
- **Problem**: Can't select domain when adding route
- **Fix**: Must add a domain to Cloudflare account first (buy domain or use Pages/Workers subdomain - but Pages/Workers don't work for Tunnels)

### Health Check Fails
- **Problem**: New tunnel URL returns 502 or timeout
- **Fix**: Wait 10-15 seconds after URL appears for prechecks to complete, then test `/api/health`

### Named Tunnel Does NOT Auto-Get cfargotunnel.com URL (CRITICAL 2026-07-25)
- **Problem**: Named tunnels do NOT automatically get a `https://<name>.cfargotunnel.com` URL. The `cfargotunnel.com` domain is Cloudflare's internal domain — you cannot just "route DNS" to it.
- **Root Cause**: Many docs imply named tunnels get a stable cfargotunnel.com URL automatically. They do NOT.
- **Fix**: You MUST configure a Public Hostname in Cloudflare Zero Trust Dashboard:
  1. Go to **Zero Trust → Networks → Tunnels → [your tunnel]**
  2. Click **Public Hostname** tab
  3. Add route: Subdomain (e.g., `aether-rag`), Domain (must be a domain you own in Cloudflare), Service: `http://localhost:8000`
- **If you don't own a domain**: Use quick tunnels (`cloudflared tunnel --url http://localhost:8000`) which give you a random `https://<random>.trycloudflare.com` URL immediately — but it changes on every restart.
- **Note: The script now uses `quick-tunnel` mode to avoid this issue, which is why the cron job runs -- it gives a new URL daily.

### Manual Run vs Cron Job (2026-08-10) — KEY LESSON
- **Cron job works**: Hermes cron resolves `script: "daily_tunnel_restart.py"` from the skill's `references/` directory automatically
- **Manual run failed**: Running `python C:\Users\valte\project_rag\daily_tunnel_restart.py` failed because that file does NOT exist in project_rag
- **Correct manual run**: Use the full path: `python C:\Users\valte\AppData\Local\hermes\skills\devops\cloudflare-tunnel-management\references\daily_tunnel_restart.py`
- **Root cause**: The cron job configuration uses just the script name (no path), relying on Hermes' internal script resolution. Manual terminal runs must use the absolute path to the skill's references directory.
- **Script location**: Always in `skills/<category>/<skill-name>/references/` — NOT in the project directory

### Cron Job Deduplication (2026-08-01) — LESSON LEARNED
- **Issue**: TWO cron jobs were running the same daily tunnel restart at 8 AM:
  1. `dde5889befde` (enabled) → runs working script at `C:\\\\Users\\\\valte\\\\project_rag\\\\daily_tunnel_restart.py` (quick tunnel, no admin needed) ✅
  2. `abb4650a1c91` (disabled) → runs BROKEN script at `C:\\\\Users\\\\valte\\\\AppData\\\\Local\\\\hermes\\\\scripts\\\\daily_tunnel_restart.py` (tries `sc stop/start` Windows service commands requiring admin) ❌
- **Root Cause**: The Hermes scripts directory contains a legacy service-management script that assumes admin privileges. Cron runs as user `valte` without admin rights.
- **Fix**: Disabled the broken duplicate cron job (`abb4650a1c91`). The working job `dde5889befde` continues to run correctly.
- **Lesson**: When creating cron jobs, verify the script being called matches the environment's privilege level. Quick tunnels work in user context; Windows service management requires Administrator.

### Cron Job Configuration (2026-08-07) — UPDATED
- **Active cron job**: `dde5889befde` (enabled) — runs daily at 8 AM
- **Script reference**: `daily_tunnel_restart.py` (Hermes cron resolves this from skills/references directory)
- **Actual script location**: `C:\Users\valte\AppData\Local\hermes\skills\devops\cloudflare-tunnel-management\references\daily_tunnel_restart.py`
- **Disabled duplicate**: `abb4650a1c91` — runs from `C:\Users\valte\project_rag` with broken service-management script (requires admin)
- **Note**: The cron job config shows `script: "daily_tunnel_restart.py"` without full path — Hermes cron resolves it from the skills references directory. Last successful run: 2026-08-07T08:59:33 (status: ok)
- **Recommendation**: Keep cron job as-is — it works. Do NOT change to absolute path unless Hermes cron resolution changes.

### Model.Options Timeout on Dashboard (2026-07-25)
- **Problem**: Hermes dashboard request to `/api/model/options` (or JSON-RPC `model.options`) times out
- **Root Cause**: The endpoint calls provider APIs (OpenRouter, Anthropic, etc.) to fetch live model catalogs. If provider APIs are slow/unreachable, the request times out.
- **Fix**: 
  - Add request timeouts to provider API calls in `hermes_cli/inventory.py`
  - Use disk cache (1h TTL) by default — only `refresh=true` should hit live APIs
  - Consider making dashboard model picker load async with loading state

### Quick Tunnel Daily Restart Script
Location: `references/daily_tunnel_restart.py`

Key features:
- Kills all cloudflared processes
- Starts fresh quick tunnel detached
- Extracts trycloudflare.com URL from stdout
- Verifies `/api/health` endpoint
- Reports new URL with all endpoints

### Actual Working Configuration (2026-08-07)
- **Cron job path**: `C:\Users\valte\AppData\Local\hermes\skills\devops\cloudflare-tunnel-management\references\daily_tunnel_restart.py`
- **Local server**: Runs from worktree at `C:\Users\valte\project_rag.worktrees\ngrok-hosting-aether-minds-app\server.py` on port 8000
- **cloudflared binary**: `C:\Program Files (x86)\cloudflared\cloudflared.exe`
- **Quick tunnel URL format**: `https://<random-words>.trycloudflare.com` (changes daily)
- **Verification**: All endpoints tested and working: `/api/health`, `/api/chat`, `/knowledge`, `/`, `/download/aether`
- **Known issue**: RAG knowledge base has 0 chunks (`"chunks":0` in `/api/health`), so chat queries fail with "Number of requested results 0, cannot be negative, or zero. in query." - PDFs need to be uploaded via `/api/upload` or ChromaDB rebuilt
- **Process**: 
  1. Kill existing cloudflared processes (`taskkill /F /IM cloudflared.exe`)
  2. Start local RAG server (`python server.py` from worktree dir)
  3. Start quick tunnel detached (`cloudflared tunnel --url http://localhost:8000`)
  4. Wait 10s for prechecks to complete
  5. Extract URL from cloudflared stdout (appears after "Your quick Tunnel has been created!")
  6. Verify `/api/health` returns 200 OK
  7. Report new daily URL

### Windows Service vs Quick Tunnel (2026-08-06) — KEY LESSON
- **Windows service approach** (`sc stop/start Cloudflared`): Requires Administrator privileges → FAILS in cron (runs as user `valte`)
- **Quick tunnel approach** (`cloudflared tunnel --url http://localhost:8000`): Works in user context → SUCCESS in cron
- The legacy script in `C:\Users\valte\AppData\Local\hermes\scripts\daily_tunnel_restart.py` uses Windows service commands and will fail in cron
- The working script uses quick tunnel mode and works correctly

## References
- `references/daily_tunnel_restart.py` - Daily restart script with URL extraction
- `references/cloudflare-dashboard-steps.md` - Dashboard configuration steps