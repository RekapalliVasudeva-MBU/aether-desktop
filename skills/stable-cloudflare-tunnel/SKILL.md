---
name: stable-cloudflare-tunnel
description: Setting up stable Cloudflare named tunnels (vs quick tunnels) with Windows service installation for persistent public URLs that survive reboots.
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
category: devops
tags: [cloudflare, tunnel, named-tunnel, windows-service, cloudflared, uptime]
---

# Stable Cloudflare Named Tunnel Skill

## Overview
Quick tunnels (`cloudflared tunnel --url http://localhost:8000`) generate a new random URL on every restart. For production use, **named tunnels** provide a stable URL and can run as a Windows service for auto-start on boot.

## Quick Tunnel vs Named Tunnel

| Aspect | Quick Tunnel | Named Tunnel |
|--------|--------------|--------------|
| URL Stability | Changes every restart | Fixed (configured via Cloudflare Dashboard) |
| Persistence | Dies when terminal closes | Runs as Windows service (auto-start) |
| Auth | None needed | Requires API token + tunnel token |
| Management | Manual | Dashboard manageable |

## Setup Steps

### 1. Create Named Tunnel (One-Time)
```bash
# Install cloudflared as Windows service
cloudflared.exe service install

# Login (opens browser)
cloudflared.exe tunnel login

# Create named tunnel
cloudflared.exe tunnel create aether-rag

# Get the tunnel token (save this securely!)
cloudflared.exe tunnel token aether-rag
```

### 2. Configure Public Hostname in Cloudflare Dashboard (REQUIRED)
**Named tunnels do NOT automatically get a `<name>.cfargotunnel.com` URL.** You must configure a public hostname:

1. Go to **Cloudflare Dashboard → Zero Trust → Networks → Tunnels**
2. Click your tunnel (e.g., **aether-rag**, ID: `9bceec42-2828-4c64-8b91-e1138509b996`)
3. Go to **Public Hostname** tab
4. Add a hostname:
   - **Subdomain**: `aether-rag` (or your choice)
   - **Domain**: Select a domain you own in Cloudflare (NOT cfargotunnel.com)
   - **Service**: `http://localhost:8000`
5. Save — the tunnel now serves at `https://aether-rag.yourdomain.com`

**Alternative**: If you don't own a domain, use a quick tunnel instead (see below).

### 3. Configure Server to Launch Named Tunnel
In `server.py` lifespan/startup:

```python
def _open_cloudflare_tunnel() -> tuple:
    token = CONFIG.get("cloudflare_tunnel_token", "")
    if not token:
        return None, None
    
    import subprocess, time, requests
    proc = subprocess.Popen(
        ["./cloudflared.exe", "tunnel", "--no-autoupdate", "run", "--token", token],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        cwd="/c/Users/valte"
    )
    time.sleep(8)
    tunnel_name = CONFIG.get("cloudflare_tunnel_name", "aether-rag")
    # NOTE: The public URL is whatever you configured in the Cloudflare Dashboard,
    # NOT automatically https://{tunnel_name}.cfargotunnel.com
    # Store the actual URL in CONFIG or fetch from dashboard API
    return proc, CONFIG.get("cloudflare_tunnel_public_url", "")
```

### 4. Windows Service (Auto-Start on Boot)
```bash
# Install cloudflared as service (runs the named tunnel)
# MUST run as Administrator
cloudflared.exe service install

# The service reads config from %USERPROFILE%\.cloudflared\config.yml
# Create config.yml:
tunnel: <tunnel-uuid>
credentials-file: %USERPROFILE%\.cloudflared\<tunnel-uuid>.json
ingress:
  - hostname: aether-rag.yourdomain.com  # Must match dashboard config
    service: http://localhost:8000
  - service: http_status:404
```

### 5. Config Schema (server_config.json)
```json
{
  "cloudflare_tunnel_token": "<tunnel-token-from-step-1>",
  "cloudflare_tunnel_name": "aether-rag",
  "cloudflare_tunnel_public_url": "https://aether-rag.yourdomain.com"  // Optional: configured URL for health checks
}
```

### 6. Uptime Monitoring Endpoint
Add `/api/uptime` for UptimeRobot / custom monitoring:

```python
@app.get("/api/uptime")
async def uptime_endpoint():
    stats = get_uptime_stats()
    health = await health()  # reuse existing
    return {**stats, "health": health, "timestamp": datetime.now(timezone.utc).isoformat()}
```

Point UptimeRobot to `https://aether-rag.yourdomain.com/api/uptime` with keyword check for `"healthy": true`.

## Key Files
- `references/cloudflare-named-tunnel-setup.md` — step-by-step with screenshots
- `references/cloudflared-config.yml` — template for Windows service
- `references/uptime-monitoring.md` — UptimeRobot / custom monitor setup
- `references/session-2026-07-23-named-tunnel-fallback.md` — session log: quick tunnel works but URL changes daily; named tunnel setup requires Administrator PowerShell for `sc delete` / `service install`; quick tunnel works as fallback when named tunnel stuck in STOP_PENDING
- `references/session-2026-07-25-named-tunnel-correction.md` — **NEW**: Critical correction: named tunnels do NOT auto-get cfargotunnel.com URLs; must configure Public Hostname in Cloudflare Zero Trust Dashboard; quick tunnels give random .trycloudflare.com URLs immediately but change on restart
- `references/session-2026-07-25-model-options-timeout.md` — Investigation: `model.options` timeout is provider API latency (OpenRouter/Anthropic model catalog fetches), not Hermes bug; fix by adding timeouts in `inventory.py`
- `references/daily-quick-tunnel-restart.md` — Daily cron script: kills old cloudflared, starts fresh quick tunnel, extracts .trycloudflare.com URL, verifies health, reports all endpoints; zero-config fallback when named tunnel not available

## Session Learnings (2026-07-23)
- **Confirmed**: Quick tunnel (`cloudflared tunnel --url http://localhost:8000`) works immediately but URL changes on every restart
- **Confirmed**: Named tunnel requires valid token from Cloudflare dashboard + `cloudflared.exe service install` as Administrator
- **Confirmed**: Service stuck in `STOP_PENDING` requires `taskkill /F /IM cloudflared.exe` then `sc delete Cloudflared` from **Administrator** PowerShell
- **Confirmed**: Service install from non-elevated shell fails with "Access denied" (exit code 5)
- **Confirmed**: Quick tunnel works as reliable fallback when named tunnel service is stuck; server config supports both with named tunnel attempted first
- **Config**: `cloudflare_tunnel_token` and `cloudflare_tunnel_name` in `server_config.json`; server auto-starts named tunnel if token present, falls back to external quick tunnel
- **Confirmed**: Quick tunnel works as reliable no-admin fallback; URL changes on restart but works immediately; server config supports dual-mode (named tunnel attempted first, falls back to external quick tunnel)
- **Server enhancements**: Added `/api/app/update-check` (desktop app auto-update polling), `/api/uptime` (UptimeRobot monitoring), citation-enriched RAG streaming
- **Dual-mode architecture**: Server auto-detects token → named tunnel; no token → external quick tunnel fallback; no code changes needed to switch modes

## Session Learnings (2026-07-25) — CRITICAL CORRECTION
- **Named tunnels do NOT automatically get a `https://<name>.cfargotunnel.com` URL**. The `cfargotunnel.com` domain is Cloudflare's internal domain; you cannot just "route DNS" to it.
- **You MUST configure a Public Hostname in Cloudflare Zero Trust Dashboard** (Zero Trust → Networks → Tunnels → [your tunnel] → Public Hostname tab).
- The hostname MUST be on a domain you own/manage in Cloudflare (e.g., `aether-rag.yourdomain.com`).
- Quick tunnels (`cloudflared tunnel --url http://localhost:8000`) give you a random `https://<random>.trycloudflare.com` URL immediately with zero config — but it changes on every restart.
- **If you don't own a domain, use quick tunnels** — they work instantly for testing/demos. Named tunnels are for production with a stable custom domain.
- Today's tunnel (ID: `9bceec42-2828-4c64-8b91-e1138509b996`, name: `aether-rag`) connected successfully but has no Public Hostname configured → `https://aether-rag.cfargotunnel.com` times out.

## Daily Quick Tunnel Restart (2026-08-01)
- **Script**: `C:\\Users\\valte\\project_rag\\daily_tunnel_restart.py` runs as daily Hermes cron job
- **Workflow**: Kills old cloudflared → starts fresh quick tunnel → extracts `.trycloudflare.com` URL → verifies `/api/health` → reports all endpoints
- **Zero-config**: No Cloudflare account, no auth token, no Dashboard config needed
- **URL changes daily**: New random subdomain on every restart (e.g., `scholarship-lexington-flying-remove.trycloudflare.com`)
- **Verification**: Health check passes with `{"status":"ok","chunks":0,"queue_position":0,"current_request":false,"gpu_model":"richardyoung/qwythos-9b-abliterated:Q4_K_M","postgres":false}`
- **Reference**: `references/daily-quick-tunnel-restart.md` — full script documentation and evolution from ngrok to cloudflared

## Cron Job Deduplication (2026-08-01) — LESSON LEARNED
- **Issue**: TWO cron jobs were running the same daily tunnel restart at 8 AM:
  1. `dde5889befde` (enabled) → runs working script at `C:\\Users\\valte\\project_rag\\daily_tunnel_restart.py` (quick tunnel, no admin needed) ✅
  2. `abb4650a1c91` (disabled) → runs BROKEN script at `C:\\Users\\valte\\AppData\\Local\\hermes\\scripts\\daily_tunnel_restart.py` (tries `sc stop/start` Windows service commands requiring admin) ❌
- **Root Cause**: The Hermes scripts directory contains a legacy service-management script that assumes admin privileges. Cron runs as user `valte` without admin rights.
- **Fix**: Disabled the broken duplicate cron job (`abb4650a1c91`). The working job `dde5889befde` continues to run correctly.
- **Lesson**: When creating cron jobs, verify the script being called matches the environment's privilege level. Quick tunnels work in user context; Windows service management requires Administrator.

## Troubleshooting
| Symptom | Fix |
|---------|-----|
| `cfargotunnel.com` returns 502/timeout | No Public Hostname configured in Cloudflare Dashboard |
| Service won't start | Run `cloudflared.exe service install` as Administrator |
| URL changes on reboot | You're using quick tunnel; switch to named tunnel + Public Hostname |
| 503 on first request | Tunnel needs 5-10s after service start; add retry logic |
| "Access denied" on service install | Must run PowerShell/cmd as Administrator |

## Verification
```bash
# Test local server
curl http://localhost:8000/api/health
# Should return {"status": "ok", ...}

# Test public URL (after Public Hostname configured in Dashboard)
curl https://aether-rag.yourdomain.com/api/health

# Test auto-start
shutdown /r /t 0
# After reboot, URL should work without manual commands
```