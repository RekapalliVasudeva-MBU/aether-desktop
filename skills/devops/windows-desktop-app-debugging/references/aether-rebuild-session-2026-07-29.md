# Aether Desktop App - Complete Rebuild & Launch Session (2026-07-29)

## Summary
User requested full rebuild of Aether desktop app (PyWebView + FastAPI + PyInstaller) with native window opening and RAG chat tested.

## Key Issues Fixed This Session

### 1. Entry Point Mismatch (CRITICAL)
**Problem**: `build_entry.py` called `uvicorn.run(app, ...)` directly, bypassing the WebView launcher entirely.
**Fix**: Updated `build_entry.py` to call `desktop_app_fixed.main()` which:
- Starts backend in daemon thread
- Waits for backend readiness
- Calls `_launch_webview(port)` to open native window

### 2. Missing Module Import in Backend Thread
**Problem**: `_run_backend()` imported from `aether.desktop_app_impl` which doesn't exist in frozen bundle.
**Fix**: Changed to `from desktop_app_fixed import app` (local module)

### 3. Frozen Build Configuration
**Required PyInstaller flags:**
```bash
--add-data "aether;aether" \
--add-data "desktop_ui;desktop_ui" \
--hidden-import aether --hidden-import aether.config \
--hidden-import aether.agent --hidden-import aether.pdf_store \
--hidden-import aether.rag --hidden-import aether.provider \
--hidden-import aether.tools --hidden-import aether.memory \
--hidden-import aether.skills --hidden-import webview \
--hidden-import uvicorn.logging --hidden-import uvicorn.loops.auto \
--hidden-import uvicorn.protocols.http.auto --hidden-import uvicorn.protocols.websockets.auto \
--hidden-import uvicorn.lifespan.on --hidden-import win32com --hidden-import win32com.client --hidden-import winshell
```

### 4. WebView2 Runtime (Pre-requisite)
Verified installed on user's machine at: `C:\Program Files (x86)\Microsoft\EdgeWebView\Application\`

## Files Modified
1. `build_entry.py` - Fixed entry point to call `main()`
2. `desktop_app_fixed.py` - Fixed `_run_backend()` import, added `main()` export
3. `build_aether.py` - Already had correct PyInstaller flags

## Build Commands (PowerShell)

### Clean Build
```powershell
# Kill any running processes
$procs = Get-Process | Where-Object {$_.ProcessName -like "*Aether*" -or $_.ProcessName -like "*webview*"}
foreach ($p in $procs) { Stop-Process -Id $p.Id -Force }

# Clean artifacts
Remove-Item -Recurse -Force "dist_build", "build_aether" -ErrorAction SilentlyContinue

# Rebuild
python build_aether.py
```

### Launch Frozen App
```powershell
# This OPENS THE NATIVE WINDOW
C:\Users\valte\aether\dist_build\Aether\Aether.exe
```

## API Test Commands (CMD)

### Health Check
```cmd
curl -s http://127.0.0.1:8732/api/health
```

### RAG Chat Test
```cmd
curl -X POST http://127.0.0.1:8732/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"mode\":\"rag\",\"message\":\"what is rag\",\"session_id\":null}"
```

## Expected Results
- ✅ Native pywebview/WebView2 window opens (1280x840, title: "Aether — AI Agent + Personal RAG")
- ✅ Backend serves on http://127.0.0.1:8732
- ✅ `/api/health` returns `{"ok":true}`
- ✅ `/api/chat` (RAG mode) returns streaming SSE with grounded answer

## User's Environment
- Source: `C:\Users\valte\aether\`
- Installed: `C:\Users\valte\AppData\Local\Aether\Aether.exe`
- WebView2: `C:\Program Files (x86)\Microsoft\EdgeWebView\Application\137.0.3296.83\msedgewebview2.exe`

## Troubleshooting (if window doesn't appear)
1. Check Task Manager for "Aether.exe" process
2. Check `aether_stdout.log` in `%USERPROFILE%\AppData\Local\Aether\`
3. Kill all Aether/webview processes and relaunch
4. Verify WebView2 Runtime is installed (it is)

## Skill Updates Needed
- [x] `windows-desktop-app-debugging` - Added entry point fix section
- [ ] `windows-desktop-app-packaging` - May need rebuild sequence update