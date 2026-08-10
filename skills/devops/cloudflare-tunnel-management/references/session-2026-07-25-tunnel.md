# Session Learnings: 2026-07-25 — Tunnel URL Management

## Context
During the RAG server fix session, the Cloudflare named tunnel failed to start:
```
⚠️ Failed to start Cloudflare named tunnel: [WinError 2] The system cannot find the file specified
```

The fallback was using a quick tunnel (`cloudflared tunnel --url http://localhost:8000`) which works but generates a new random URL every restart.

## Key Learnings

### 1. Named Tunnel Prerequisites Not Met
The server code attempts to start a named tunnel at startup (see `server.py` lifespan hook):
```python
ngrok_ref = _open_tunnel()  # returns (ngrok, public_url) or (None, None)
```

But the named tunnel setup requires:
1. Cloudflare account with domain added
2. `cloudflared tunnel login` completed (creates `~/.cloudflared/cert.pem`)
3. Tunnel created: `cloudflared tunnel create aether-rag`
4. DNS route configured: `cloudflared tunnel route dns aether-rag aether-rag.cfargotunnel.com`
5. Token obtained from dashboard and set in `server_config.json` → `cloudflare_tunnel_token`

**Without cert.pem**, the named tunnel fails with "Cannot determine default origin certificate path" — which is exactly what happened.

### 2. Quick Tunnel Works as Fallback
```bash
cd /c/Users/valte && ./cloudflared tunnel --url http://localhost:8000
```
This runs in background and provides a temporary URL (e.g., `https://random-words.trycloudflare.com`). The URL changes on every restart.

### 3. URL Extraction from Quick Tunnel Output
The tunnel output contains the URL after:
```
2026-07-25T08:44:34Z INF Your quick Tunnel has been created! URL: https://random-words.trycloudflare.com
```

Can extract with regex:
```python
import re
url_match = re.search(r'URL: (https://[\w-]+\.trycloudflare\.com)', output)
```

### 4. Health Check Timing
After the URL appears, wait 10-15 seconds before testing `/api/health` — Cloudflare runs prechecks.

### 5. Current Setup Status
| Component | Status | Notes |
|-----------|--------|-------|
| Named tunnel | ❌ Failed | No cert.pem, token in config but auth not done |
| Quick tunnel | ✅ Running | Background process `proc_2c4b754e88f4` |
| Stable URL | ❌ Not available | Would need domain + cert.pem |
| Daily cron | ⚠️ Exists | `daily_tunnel_restart.py` but may not handle quick tunnel properly |

## Action Items for Stable URL
1. **Option A**: Complete named tunnel setup
   - Add domain to Cloudflare
   - Run `cloudflared tunnel login`
   - Create tunnel, route DNS
   - Update `server_config.json` with token
   - Install as Windows service

2. **Option B**: Accept quick tunnel + daily cron reporting
   - Cron job restarts tunnel daily at 8 AM
   - Extracts new URL and reports it
   - URL changes daily but users get notification

## Related Files
- `C:\Users\valte\project_rag\server.py` — lifespan hook calls `_open_tunnel()`
- `C:\Users\valte\project_rag\server_config.json` — has `cloudflare_tunnel_token` and `cloudflare_tunnel_name`
- `C:\Users\valte\project_rag\daily_tunnel_restart.py` — cron script for daily restart
- `C:\Users\valte\cloudflared.exe` — binary location