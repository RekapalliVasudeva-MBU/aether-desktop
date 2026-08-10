# Daily Quick Tunnel Restart Script

## Overview
A Python script that runs as a daily cron job to restart the cloudflared quick tunnel to localhost:8000, extract the new `.trycloudflare.com` URL, verify it works, and report the new daily URL with all endpoints.

## Usage
```bash
python C:\Users\valte\project_rag\daily_tunnel_restart.py
```

## Behavior
1. **Stops old tunnel** - `taskkill /F /IM cloudflared.exe`
2. **Starts new quick tunnel** - `cloudflared tunnel --url http://localhost:8000 --no-autoupdate`
3. **Extracts URL** - Parses stderr for `https://*.trycloudflare.com` pattern
4. **Verifies** - Calls `/api/health` endpoint, expects `{"status":"ok"}`
5. **Reports** - Prints all endpoints (Website, Health, Chat API, Download, RAG Docs)

## Key Points
- **Quick tunnels** give a new random `.trycloudflare.com` URL on every restart
- No Cloudflare account or auth token needed
- Works immediately without Dashboard configuration
- URL changes daily (or on every restart)
- Ideal for development/testing/demos where stable URL isn't required

## Script Evolution
- **Original**: Used `pyngrok` with ngrok auth token (failed when token not set)
- **Current**: Uses `cloudflared` subprocess directly, no auth required
- **Fallback pattern**: When named tunnel isn't configured or fails, quick tunnel is zero-config fallback

## Verification Output (2026-08-01)
```
Daily cloudflared Tunnel URL - 2026-08-01
Website:     https://scholarship-lexington-flying-remove.trycloudflare.com
Health:      https://scholarship-lexington-flying-remove.trycloudflare.com/api/health
Chat API:    https://scholarship-lexington-flying-remove.trycloudflare.com/api/chat
Download:    https://scholarship-lexington-flying-remove.trycloudflare.com/download/aether
RAG Docs:    https://scholarship-lexington-flying-remove.trycloudflare.com/knowledge
```

## Cron Integration
Runs daily via Hermes cron. Output is captured and delivered to user.
No manual intervention needed - fully autonomous.

## Related Files
- `daily_tunnel_restart.py` - The script itself (in project_rag/)
- `server.py` - The FastAPI server running on localhost:8000 with `/api/health`