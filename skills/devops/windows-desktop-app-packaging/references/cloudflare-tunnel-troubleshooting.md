# Cloudflare Named Tunnel Troubleshooting

## Service Install Failed: "Illegal base64 data at input byte 6"

**Cause:** The tunnel token was truncated (used `eyJhIj...eiJ9` instead of full token).

**Fix:** Use the FULL token from Cloudflare Dashboard → Zero Trust → Networks → Tunnels.

```powershell
C:\Users\valte\cloudflared.exe service install eyJhIjoiMmIwZDViZGY3YjMxZjE5NTlmZjgwODBhNzU0NmY0MGEiLCJ0IjoiOWJjZWVjNDItMjgyOC00YzY0LThiOTEtZTExMzg1MDliOTk2IiwicyI6Ik5UazBZV00wWVRndFlqQmxZeTAwWldGa0xUZzNZemN0T0dVeFlXSXpOemxrT1RVeiJ9
```

## Service Stuck in STOP_PENDING

**Symptoms:**
- `sc query Cloudflared` shows `STATE: 3 STOP_PENDING`
- `sc delete Cloudflared` returns "Access denied"

**Fix (run in Admin PowerShell):**
```powershell
taskkill /F /IM cloudflared.exe
sc delete Cloudflared
C:\Users\valte\cloudflared.exe service install <FULL_TOKEN>
Get-Service Cloudflared
```

## Service Installed but URL Not Working

**Symptoms:**
- `Get-Service Cloudflared` shows "Running"
- `https://aether-rag.cfargotunnel.com` times out

**Root Cause:** Named tunnel requires a Public Hostname configured in Cloudflare Dashboard.

**Fix:**
1. Go to Cloudflare Dashboard → Zero Trust → Networks → Tunnels
2. Click your tunnel (`aether-rag`)
3. Add Public Hostname: `aether-rag` → `cfargotunnel.com`
4. Save
5. Restart project_rag server (it will auto-start the named tunnel)

## Quick Tunnel vs Named Tunnel

| Feature | Quick Tunnel | Named Tunnel |
|---------|-------------|--------------|
| Setup | `cloudflared tunnel --url http://localhost:8000` | Requires Dashboard config + service install |
| Admin rights | No | Yes (service install) |
| URL stability | Changes on restart | Permanent `*.cfargotunnel.com` |
| Hostname config | None | Dashboard → Public Hostname |
| Best for | Testing, demos | Production, permanent URLs |

**Current Working Quick Tunnel:**
```
https://revisions-flashing-elliott-uploaded.trycloudflare.com
```

**Named Tunnel (when hostname configured):**
```
https://aether-rag.cfargotunnel.com
```