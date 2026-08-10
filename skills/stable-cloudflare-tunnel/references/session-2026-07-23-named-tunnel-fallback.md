# Session 2026-07-23: Named Tunnel Setup & Quick Tunnel Fallback

## Context
User needed a stable public URL for their local RAG server (project_rag) and desktop app (Aether). Previous quick tunnel URLs changed on every restart. Attempted named tunnel setup but Windows service installation required Administrator privileges which couldn't be automated.

## What Worked (Quick Tunnel - Immediate)

```bash
# Run in background (no admin needed)
./cloudflared.exe tunnel --url http://localhost:8000
```
- URL: `https://shots-midi-context-varies.trycloudflare.com`
- Works immediately, no admin required
- URL changes on restart (quick tunnel limitation)
- Health check: `/api/health` returns 200 OK
- Download endpoint: `/download/aether` serves 183MB installer

## What Didn't Work (Named Tunnel - Requires Admin)

```powershell
# Requires Administrator PowerShell (right-click → "Run as Administrator")
taskkill /F /IM cloudflared.exe
sc delete Cloudflared
C:\Users\valte\cloudflared.exe service install <token>
Get-Service Cloudflared
```

**Failure mode**: Service stuck in `STOP_PENDING` → `sc delete` fails with "Access denied" (exit code 5) → subsequent `service install` says "service already installed".

**Root cause**: Previous service uninstall didn't fully complete → process PID 26224 held by SYSTEM → non-elevated shell can't kill it.

## Server-Side Fix: Dual Tunnel Strategy

Updated `server.py` to support both:

```python
def _open_tunnel():
    # 1. Try named tunnel if token configured
    token = CONFIG.get("cloudflare_tunnel_token", "")
    if token:
        proc, url = _open_cloudflare_tunnel(token)
        if proc and url:
            return proc, url
    
    # 2. Fallback: quick tunnel (launched externally)
    print("Public URL: run 'cloudflared tunnel --url http://localhost:8000' separately")
    return None, None
```

**Config** (`server_config.json`):
```json
{
  "cloudflare_tunnel_token": "<token-from-dashboard>",
  "cloudflare_tunnel_name": "aether-rag"
}
```

**Result**: Named tunnel auto-starts if token valid; falls back to external quick tunnel otherwise. No code changes needed when switching between modes.

## Quick Tunnel URL (Current Working)

| Service | URL |
|---------|-----|
| Website | https://shots-midi-context-varies.trycloudflare.com |
| Health | https://shots-midi-context-varies.trycloudflare.com/api/health |
| Download | https://shots-midi-context-varies.trycloudflare.com/download/aether |
| Uptime | https://shots-midi-context-varies.trycloudflare.com/api/uptime |
| App Update Check | https://shots-midi-context-varies.trycloudflare.com/api/app/update-check |

## Server Enhancements Added

1. **App Auto-Update Check** (`/api/app/update-check`):
   - Returns current version, download URL, changelog
   - Desktop app polls this on launch

2. **Uptime Monitoring** (`/api/uptime`):
   - Returns uptime, health, timestamp
   - For UptimeRobot / custom monitors

3. **Citation-Enriched RAG**:
   - `sync_hybrid_search_with_citations()` returns source_file, page, headings, relevance_score
   - Citations streamed in final SSE message

## Quick Tunnel Reliability Notes

- Quick tunnel runs as background process (no admin)
- URL changes on restart (acceptable for dev)
- Auto-restart: add to startup script or systemd/user service
- For production: complete named tunnel setup with Admin once

## Config for Quick Tunnel (server_config.json)

```json
{
  "cloudflare_tunnel_token": "",
  "cloudflare_tunnel_name": "aether-rag",
  "openrouter_api_key": "",
  "allow_download": true
}
```

Empty token → server uses quick tunnel fallback.