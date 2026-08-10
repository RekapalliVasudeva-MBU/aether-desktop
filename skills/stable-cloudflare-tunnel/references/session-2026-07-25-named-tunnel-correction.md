# Session 2026-07-25: Named Tunnel Correction

## Critical Discovery

**Named tunnels do NOT automatically provide a `https://<name>.cfargotunnel.com` URL.**

This was a fundamental misunderstanding in the original skill documentation. The `cfargotunnel.com` domain is Cloudflare's internal routing domain — you cannot simply "route DNS" to it or expect it to work out of the box.

## What Actually Happened Today

1. **Tunnel created**: `cloudflared.exe tunnel create aether-rag` → ID: `9bceec42-2828-4c64-8b91-e1138509b996`
2. **Token obtained**: `cloudflared.exe tunnel token aether-rag` → token saved in `server_config.json`
3. **Tunnel connected**: Running `cloudflared.exe tunnel run --token <token>` successfully connected (logs show QUIC connections to Mumbai/Bombay PoPs)
4. **BUT**: No Public Hostname configured in Cloudflare Zero Trust Dashboard
5. **Result**: `https://aether-rag.cfargotunnel.com` times out — because it doesn't exist as a routable hostname

## The Fix

**You MUST configure a Public Hostname in Cloudflare Zero Trust Dashboard:**

1. Go to: https://dash.cloudflare.com/ → Zero Trust → Networks → Tunnels
2. Click tunnel: **aether-rag** (ID: `9bceec42-2828-4c64-8b91-e1138509b996`)
3. Click **Public Hostname** tab
4. Click **Add a public hostname**
5. Fill in:
   - **Subdomain**: `aether-rag` (or any subdomain)
   - **Domain**: Select a domain you own in Cloudflare (e.g., `yourdomain.com`)
   - **Type**: HTTP
   - **URL**: `http://localhost:8000`
6. Save

The tunnel will then be accessible at `https://aether-rag.yourdomain.com`

## Quick Tunnel Alternative

If you don't own a domain or need immediate access:

```bash
cd /c/Users/valte && ./cloudflared.exe tunnel --url http://localhost:8000
```

This gives you a random `https://<random>.trycloudflare.com` URL **immediately** with zero configuration — but it changes on every restart.

## Server Config Dual-Mode

The server (`server.py`) already supports both modes:
- **Named tunnel**: If `cloudflare_tunnel_token` is set in config → attempts to start named tunnel
- **Quick tunnel fallback**: If no token or named tunnel fails → instructs user to run quick tunnel externally

No code changes needed to switch modes.

## Files Modified This Session

- `server.py`: Added `_open_cloudflare_tunnel()` with named tunnel logic (attempts named tunnel first, falls back to quick tunnel)
- `server_config.json`: Added `cloudflare_tunnel_token` and `cloudflare_tunnel_name`
- This skill: Updated with critical correction about Public Hostname requirement

## Verification

```bash
# Local (always works)
curl http://localhost:8000/api/health

# Quick tunnel (works immediately, URL changes on restart)
./cloudflared.exe tunnel --url http://localhost:8000
# Returns: https://abc123.trycloudflare.com

# Named tunnel (requires Public Hostname in Dashboard)
# After configuring hostname in Dashboard:
curl https://aether-rag.yourdomain.com/api/health
```