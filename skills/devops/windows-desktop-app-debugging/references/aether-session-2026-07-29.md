# Aether Session - 2026-07-29: Critical Frozen App Bugs

## Context
User reported app opens but "nothing is working inside". Analyzed `aether_stdout.log` from installed app at `C:\Users\valte\AppData\Local\Aether\`.

## Log Analysis - Key Errors

### 1. UnboundLocalError: `_webview2_installed`
```
Traceback (most recent call last):
  File "C:\Users\valte\aether\desktop_app.py", line 1380, in <module>
    main()
  File "C:\Users\valte\aether\desktop_app.py", line 1201, in main
    print(f"[desktop] WebView2 installed check: {_webview2_installed()}")
UnboundLocalError: cannot access local variable '_webview2_installed' where it is not associated with a value
```
**Root cause**: Function `_webview2_installed` defined inside `if not _webview2_installed():` block but called at module level.

### 2. Session Sort TypeError: WindowsPath unary minus
```
TypeError: bad operand type for unary -: 'WindowsPath'
```
**Location**: `desktop_app.py` line 96 in `_list_sessions`
**Cause**: `lambda f: -f.stat().st_mtime` fails on Windows Path objects

### 3. JSON Decode Error: Windows backslashes
```
json.decoder.JSONDecodeError: Invalid \escape: line 1 column 12 (char 11)
```
**Location**: `desktop_app.py` line 316 in `api_session_add_file`
**Cause**: Frontend sends Windows path `C:\Users\...` with unescaped backslashes

### 4. KeyError: 'pinned'
```
KeyError: 'pinned'
```
**Location**: `desktop_app.py` line 324 in `api_session_patch`
**Cause**: Session data missing `pinned` field (default should be False)

### 5. MCP Connection Spam (Repeated Every Few Seconds)
```
[mcp] failed to connect testmcp: [WinError 10038] An operation was attempted on something that is not a socket
[mcp] failed to connect playwright: [WinError 2] The system cannot find the file specified
[mcp] failed to connect duckduckgo_search: [WinError 2] The system cannot find the file specified
[mcp] failed to connect ddg: [WinError 2] The system cannot find the file specified
[mcp] failed to connect youtube-mcp: [WinError 2] The system cannot find the file specified
[mcp] failed to connect filesystem-mcp: [WinError 2] The system cannot find the file specified
```
**Cause**: 
- App tries to connect to ALL configured MCP servers on every request
- Most servers don't exist / npm packages not installed
- No caching — reconnects every request
- `WinError 10038` = socket error on stdio transport

## Build Configuration Issues Found

### 1. Missing `desktop_app_impl.py`
- `build_entry.py` does: `from desktop_app_impl import main as aether_main`
- But `desktop_app_impl.py` **does not exist** in source
- PyInstaller warns: `missing module named desktop_app_impl - imported by desktop_app (delayed)`

### 2. Missing `aether` package in PyInstaller build
- `build_aether.py` didn't include `--add-data "aether:aether"`
- Frozen app has no access to `aether.agent`, `aether.config`, `aether.tools`, etc.
- Results in `ModuleNotFoundError` at runtime

### 3. Singleton lock file not cleaned on crash
- Stale `aether_singleton.lock` prevents new instance launch
- App shows "another Aether instance is already running — focusing it" but can't focus

## Fixes Applied This Session

1. **Created `desktop_app_impl.py`** - Full FastAPI + pywebview implementation with all API endpoints
2. **Added `--add-data aether:aether`** to `build_aether.py` for PyInstaller
3. **Copied fixed files to installed app** at `C:\Users\valte\AppData\Local\Aether\_internal\`:
   - `desktop_app_impl.py`
   - `aether/` package
4. **Updated skill** with new pitfalls and patterns

## Verification Needed After Rebuild

- [ ] App window opens without splash animation
- [ ] Chat sidebar visible with Normal/RAG toggle
- [ ] RAG query returns answer + citations
- [ ] Session list loads without TypeError
- [ ] File attachment works (no JSON decode error)
- [ ] Session pin/unpin works (no KeyError)
- [ ] MCP connection attempts only for enabled servers
- [ ] No errors in `aether_stdout.log`

## References
- Source: `C:\Users\valte\aether\`
- Installed: `C:\Users\valte\AppData\Local\Aether\`
- Logs: `C:\Users\valte\AppData\Local\Aether\aether_stdout.log`
- Build script: `C:\Users\valte\aether\build_aether.py`

---

# Aether Session - 2026-07-29 (Evening): Frozen App Launch & RAG Fixes

## Problem Summary
User reported Aether desktop app not opening / not working over 3 days. Multiple issues:
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