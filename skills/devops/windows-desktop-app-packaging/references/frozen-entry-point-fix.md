# Aether Desktop App - Entry Point Fix for Frozen Build (2026-07-29)

## The Problem
The frozen PyInstaller build was running the FastAPI backend correctly (port 8732 responding) but **no native window opened**. The app appeared "stuck in background" with no UI.

## Root Cause
`build_entry.py` was the PyInstaller entry point. It imported the FastAPI `app` instance and called `uvicorn.run(app, ...)` directly — **completely bypassing the WebView launcher** in `desktop_app_fixed.main()`.

The proper entry point (`desktop_app_fixed.main()`) does:
1. Starts backend in daemon thread
2. Polls `/api/health` until 200 (not fixed sleep)
3. Calls `_launch_webview(port)` to open native window
4. Blocks on `webview.start()` (main thread)

## Fix Applied

### build_entry.py (BEFORE - broken)
```python
from desktop_app_fixed import app
uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
```

### build_entry.py (AFTER - correct)
```python
from desktop_app_fixed import main
main()
```

### desktop_app_fixed.py (additional fix for backend thread)
```python
# BEFORE (broken in frozen app)
from aether.desktop_app_impl import app

# AFTER (uses local app instance)
from desktop_app_fixed import app
```

## PyInstaller Flags Required
```bash
# Data bundles
--add-data "aether;aether"
--add-data "desktop_ui;desktop_ui"

# Hidden imports (all aether submodules)
--hidden-import aether --hidden-import aether.config
--hidden-import aether.agent --hidden-import aether.pdf_store
--hidden-import aether.rag --hidden-import aether.provider
--hidden-import aether.tools --hidden-import aether.memory
--hidden-import aether.skills

# WebView2 / uvicorn
--hidden-import webview --hidden-import uvicorn.logging
--hidden-import uvicorn.loops.auto --hidden-import uvicorn.protocols.http.auto
--hidden-import uvicorn.protocols.websockets.auto --hidden-import uvicorn.lifespan.on
--hidden-import win32com --hidden-import win32com.client --hidden-import winshell
```

## Launch Command (Opens Native Window)
```powershell
C:\Users\valte\aether\dist_build\Aether\Aether.exe
```

## Verification
```cmd
curl -s http://127.0.0.1:8732/api/health
# {"ok":true}

curl -X POST http://127.0.0.1:8732/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"mode\":\"rag\",\"message\":\"what is rag\",\"session_id\":null}"
# Returns streaming SSE with grounded RAG answer
```

## Key Lesson
**Never call `uvicorn.run()` directly in a PyInstaller entry point for a pywebview app.** The entry point MUST call the launcher function that:
1. Starts the server in a thread
2. Waits for readiness
3. Creates the WebView window on the main thread
4. Calls `webview.start()` which blocks the main thread

This pattern applies to ALL frozen pywebview + FastAPI desktop apps.