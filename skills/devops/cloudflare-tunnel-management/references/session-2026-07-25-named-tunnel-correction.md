# Session 2026-07-25: Named Tunnel Correction

## Summary
Today we discovered a critical misconception: **Named tunnels do NOT automatically get a `https://<name>.cfargotunnel.com` URL.**

## What Happened
- User had a named tunnel `aether-rag` (ID: `9bceec42-2828-4c64-8b91-e1138509b996`)
- Server code attempted to construct `https://aether-rag.cfargotunnel.com` automatically
- This URL never worked — it timed out
- Cloudflared connected successfully (logs showed prechecks passed, tunnel registered)
- But no Public Hostname was configured in Cloudflare Zero Trust Dashboard

## The Fix
1. Go to **Cloudflare Dashboard → Zero Trust → Networks → Tunnels → aether-rag**
2. Click **Public Hostname** tab
3. Add a route:
   - Subdomain: `aether-rag` (or your choice)
   - Domain: Must be a domain you own in Cloudflare (e.g., `yourdomain.com`)
   - Service: `http://localhost:8000`
4. Save — tunnel now serves at `https://aether-rag.yourdomain.com`

## If You Don't Own a Domain
Use quick tunnels instead:
```bash
cloudflared tunnel --url http://localhost:8000
```
This gives you a random `https://<random>.trycloudflare.com` URL instantly — but it changes on every restart.

## Server Code Impact
The server's `_open_cloudflare_tunnel()` function needs updating:
- Remove assumption that `https://{tunnel_name}.cfargotunnel.com` works
- Either fetch the actual URL from Cloudflare API, or require it in config as `cloudflare_tunnel_public_url`
- Fallback to quick tunnel when no Public Hostname is configured

## Model.Options Timeout
Also discovered: Hermes dashboard `/api/model/options` (and `model.options` JSON-RPC) times out because it calls live provider APIs (OpenRouter, Anthropic, etc.) to fetch model catalogs. The 1h disk cache should prevent this, but `refresh=true` or cache misses hit live APIs.

Fix: Add request timeouts in `hermes_cli/inventory.py` provider probing code.