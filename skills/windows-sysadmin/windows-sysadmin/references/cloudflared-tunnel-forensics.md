# Cloudflared Tunnel Forensics (verified recipe)

Goal: confirm a local app (e.g. project_rag on :8000) is exposed publicly via a
Cloudflare tunnel, find the binary/service, and recover or recreate the public URL.

## 1. Is the local app listening?
```bash
netstat -ano | findstr :8000
# -> TCP 127.0.0.1:8000 LISTENING <pid>   (app alive locally)
```

## 2. Is the tunnel process running? As service or console?
```bash
tasklist | findstr -i cloudflared
# Note: if under "Services" column -> it's a Windows service (survives reboot)
```

## 3. Service binary path + auto-start (reliable, wmic often absent)
```bash
sc qc Cloudflared
# BINARY_PATH_NAME : C:\Users\valte\cloudflared.exe
# START_TYPE        : 2   AUTO_START  (survives reboot)
```

## 4. Is the tunnel ACTUALLY tunneling? (zombie check)
```bash
netstat -ano | findstr <cloudflared_PID>
# If NO outbound connection to Cloudflare edge (port 7844 / region*.argotunnel.com)
# -> the service is a ZOMBIE: "running" but not forwarding. No public traffic.
```

## 5. Discovery limits (why you often CANNOT recover the URL)
- Running binary exposes NO local admin API port by default.
- `Get-CimInstance Win32_Process -Filter "ProcessId=..."` returns EMPTY
  `ExecutablePath`/`CommandLine` for LocalSystem services.
- Named tunnel URL is `<uuid>.cfargotunnel.com` — known only to Cloudflare edge
  + the deleted `~/.cloudflared/<name>.json` creds. Without the Cloudflare API
  token or the creds file, the URL is unrecoverable.

## 6. Deleted-config trap (seen in this session)
If `C:\Users\valte\cloudflared.exe`, `~/.cloudflared/config.yml`,
`~/.cloudflared/<name>.json`, `~/.cloudflared/cert.pem` are ALL MISSING but the
service "runs": tunnel is live only from in-memory state. It will FAIL after any
reboot. No URL recoverable.

## 7. Recovery (NEEDS USER CONFIRMATION — binary download)
Reinstall `cloudflared.exe` (official Cloudflare binary, ~40MB) and recreate the
named tunnel:
```bash
cloudflared tunnel login            # browser login (needs token or interactive)
cloudflared tunnel create aether-rag
# write ~/.cloudflared/config.yml:
#   tunnel: <id>
#   credentials-file: ~/.cloudflared/<id>.json
#   ingress:
#     - hostname: aether-rag.<id>.cfargotunnel.com
#       service: http://localhost:8000
#     - service: http_status:404
cloudflared tunnel install aether-rag   # installs as Windows service (auto-boot)
cloudflared tunnel start aether-rag
```
Quick alternative (no config, live immediately, URL changes each restart):
`cloudflared tunnel --url http://localhost:8000` (or `cloudflared quick`).

## MSYS / git-bash path quirks (bit during diagnosis)
- `cmd /c "C:\Users\valte\cloudflared.exe ..."` DOUBLES the drive prefix ->
  `C:\c\Users\valte\...` and fails. The real path is `C:\Users\valte\cloudflared.exe`.
- `wmic` is NOT present on modern Windows here -> use `sc qc` instead.
- Inline `powershell -Command "..."` with `$()` / `{}` gets mangled by MSYS ->
  write a `.ps1` file and run `powershell -File script.ps1`.
- To run a Windows binary reliably from this shell: Python
  `subprocess.run([r"C:\Users\valte\cloudflared.exe", ...])` or a `.ps1` file.
