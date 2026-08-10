# Cloudflare Dashboard Configuration Steps

## Named Tunnel Setup (Permanent URL)

### 1. Create Tunnel
1. Go to **Cloudflare Dashboard** → **Zero Trust** → **Networks** → **Tunnels**
2. Click **Create a tunnel**
2. Name: `aether-rag` (or your preferred name)
3. Click **Save tunnel**

### 2. Get Tunnel Token
1. Click the tunnel name (`aether-rag`) to open details
2. Copy the **Tunnel Token** (long base64 string)

### 3. Install as Windows Service (Run as Administrator)
```powershell
# First, clean up any stuck service
taskkill /F /IM cloudflared.exe
sc delete Cloudflared

# Install with your token
C:\Users\valte\cloudflared.exe service install <your-token-here>
```

### 4. Configure Public Hostname (Route)
1. In tunnel details page, click **Routes** tab (or **Public Hostnames** in newer UI)
2. Click **Add route** / **Add public hostname**
3. Fill in:
   - **Subdomain**: `aether-rag`
   - **Domain**: Select your domain from dropdown (must have domain in Cloudflare account)
   - **Service**: `HTTP` → `localhost:8000`
4. Click **Save**

### 5. Verify
1. Restart project_rag server (it auto-detects named tunnel via config)
2. Test: `https://aether-rag.yourdomain.com/api/health`

---

## Quick Tunnel (Temporary) - No Dashboard Required
```bash
cloudflared tunnel --url http://localhost:8000
```
URL appears in output after "Your quick Tunnel has been created!"

---

## Important Notes

### Domain Requirement for Named Tunnels
- **You must own a domain in your Cloudflare account** to use named tunnels
- No free `cfargotunnel.com` or `pages.dev` subdomains for tunnels
- Cheap option: Buy `.xyz`, `.top`, `.site` domains (~$1-2/year on Namecheap/Porkbun)

### Quick Tunnel Limitations
- URL changes on **every restart**
- No uptime guarantee
- Good for testing, not production

### Service Stuck Fix
If service shows "StopPending" and won't install:
```powershell
# Run as Administrator
taskkill /F /IM cloudflared.exe
sc delete Cloudflared
# Then re-run: cloudflared.exe service install <token>
```

### Health Check Timing
After tunnel URL appears, wait 10-15 seconds for prechecks before testing `/api/health`