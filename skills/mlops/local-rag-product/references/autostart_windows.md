# Auto-start the local RAG site on Windows logon (reboot-survival)

## The bug this fixes
A server (`python server.py` on :8000) and ngrok tunnel started as a **chat background
process** die when the laptop reboots or the Hermes session ends. The site then goes dark
and the promise "turn on the laptop → it works" is FALSE until someone manually restarts
them. This is the single most common outage for the laptop-hosted RAG product.

## Fix: Startup folder + idempotent launcher
No admin needed. Add the RAG start to the existing `Agent_OS.cmd` in the Windows Startup
folder:

    %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Agent_OS.cmd

Full pattern (idempotent — safe to re-run, never spawns duplicates):

```bat
@echo off
cd /d C:\Users\valte\agent-os
start /min "" npx next start -p 3001

REM --- Hybrid RAG website (project_rag) - idempotent auto-start on logon ---
SET PROJ=C:\Users\valte\project_rag
SET CF=C:\Users\valte\cloudflared.exe
netstat -an | findstr ":8000 " | findstr "LISTENING" >nul || (
  start /min "" cmd /c "cd /d %PROJ% && python server.py >> "%PROJ%\server_run.log" 2>&1"
)
REM Public tunnel via cloudflared (no bandwidth cap; ngrok free quota dies on big downloads).
REM NOTE: a quick tunnel URL changes every reboot. For a stable URL, use a Cloudflare
REM account + your own domain and `cloudflared tunnel --config ...` instead.
tasklist | findstr /i "cloudflared.exe" >nul || (
  start /min "" cmd /c ""%CF%" tunnel --url http://localhost:8000 >> "%PROJ%\cf_run.log" 2>&1"
)
```

## Why this layout
- `start /min ""` launches a detached minimized window that survives the launching cmd.
- `netstat ... findstr LISTENING` -> skip if :8000 already serving (don't double-start).
- `tasklist | findstr ngrok.exe` -> skip if ngrok already running.
- Logs appended to `server_run.log` / `ngrok_run.log` for diagnosis.

## Alternative (needs admin, for pre-login start)
```bat
schtasks /Create /TN "RAGSiteAutoStart" ^
  /TR "C:\Users\valte\project_rag\start_rag_site.bat" ^
  /SC ONLOGON /IT /F
```
Denied without admin (`ERROR: Access is denied`). Startup folder is the no-admin equivalent
and runs at user logon — sufficient here.

## Verify after a reboot
1. Log on. Wait ~30-60s (ChromaDB + CrossEncoder reranker load time).
2. `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health` -> 200
3. Public URL: read `cf_run.log` for the `*.trycloudflare.com` line, or
   `curl -s http://localhost:8000/ -o /dev/null -w "%{http_code}"` locally; the
   cloudflared URL returns 200 on `/api/health` and `/`.

## Notes
- cloudflared **quick tunnel** URL changes every reboot. For a stable URL, use a free
  Cloudflare account + your own domain (`cloudflared tunnel login` + a named tunnel).
- First request after boot is slow (model/reranker warm-up); subsequent ones are fast.
- Ollama (needed by the local generator) must also be up — add `start /min "" cmd /c "ollama serve"`
  to the same file if it isn't already auto-started.
