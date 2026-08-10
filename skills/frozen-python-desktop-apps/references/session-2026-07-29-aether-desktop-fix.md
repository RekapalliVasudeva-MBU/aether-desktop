# Session: Aether Desktop App Fixes (2026-07-29)

## Problem Summary
User reported Aether desktop app not opening / not working. Multiple issues over 3 days:
1. App wouldn't open (backend refused connection)
2. "what is rag" prompt not working in RAG mode
3. Multiple crashes on frozen exe launch

## Root Causes Identified & Fixed

### 1. Entry Point Bypassing WebView Launch
**File**: `build_entry.py`
**Issue**: `uvicorn.run(app, ...)` directly, skipping the `_launch_webview()` call that opens native window
**Fix**: Changed `build_entry.py` to import and call `main()` from `desktop_app_fixed.py`

### 2. Uvicorn Logging Crash in Frozen App
**File**: `build_entry.py`
**Issue**: `ValueError: Unable to configure formatter 'default'` → `AttributeError: 'NoneType' object has no attribute 'isatty'`
**Root Cause**: Uvicorn's default formatter calls `stream.isatty()` which fails when `sys.stderr` is None in PyInstaller `--windowed` builds
**Fix**: Added custom `log_config` dict with `use_colors: False` to uvicorn.run()

### 3. FastAPI Route Typo
**File**: `desktop_app_fixed.py` line 202
**Issue**: `@api.post("/api/chat")` instead of `@app.post("/api/chat")`
**Fix**: Changed `@api.post` → `@app.post`

### 4. Missing `model` Field in ChatRequest
**File**: `desktop_app_fixed.py` line 43-47
**Issue**: `ChatRequest` model missing `model: Optional[str] = None` field
**Fix**: Added field to Pydantic model

### 5. Import Path in Backend Thread
**File**: `desktop_app_fixed.py` line 90
**Issue**: `from aether.desktop_app_impl import app` fails in frozen build
**Fix**: Changed to `from desktop_app_fixed import app` (local module)

### 6. Port Conflict on Re-launch
**Issue**: Port 8732 already in use from previous run
**Fix**: Added port availability check in `main()` with `socket.connect_ex()`

## Verification Results
All endpoints working:
- `GET /api/health` → `{"ok":true}`
- `GET /` → Full HTML UI loads
- `POST /api/chat` (mode=normal) → Streaming SSE response
- `POST /api/chat` (mode=rag) → "RAG stands for Retrieval-Augmented Generation..."

## Process
The app now runs as:
1. `build_entry.py` → calls `desktop_app_fixed.main()`
2. `main()` starts backend thread on port 8732
3. Waits 2 seconds for backend ready
4. Calls `_launch_webview(port)` → opens native WebView2 window
5. Window loads `http://127.0.0.1:8732/` → full UI

## Executable Location
`C:\Users\valte\aether\dist_build\Aether\Aether.exe`

## Command to Rebuild (if needed)
```bash
rm -rf dist_build/Aether build_aether
pyinstaller --noconfirm --onedir --windowed --name Aether \
  --icon desktop_ui/logo.ico \
  --add-data "desktop_ui;desktop_ui" \
  --add-data "aether;aether" \
  --hidden-import webview --hidden-import uvicorn.logging \
  --hidden-import uvicorn.loops.auto --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.protocols.websockets.auto --hidden-import uvicorn.lifespan.on \
  --hidden-import win32com --hidden-import win32com.client --hidden-import winshell \
  --distpath dist_build --workpath build_aether build_entry.py
```

## Key Learnings for Future
1. **Always verify frozen app launch logic** - entry point must call WebView launcher
2. **Uvicorn logging config is required** for PyInstaller `--windowed` builds
3. **Test RAG mode specifically** - it uses different agent path
4. **Kill old processes before rebuild** - file locks cause permission errors
5. **Native window ≠ browser tab** - user kept trying `http://127.0.0.1:8732` in browser