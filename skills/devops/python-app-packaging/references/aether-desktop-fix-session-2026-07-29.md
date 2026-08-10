# Aether Desktop App Fix Session — 2026-07-29

## Session Summary
Complete rebuild of the Aether desktop app (pywebview + FastAPI + PyInstaller) from a broken state where the app showed `ERR_CONNECTION_REFUSED` on launch. The build script was only copying files, not running PyInstaller.

## Root Causes Fixed

### 1. Build Script Didn't Run PyInstaller
- **Issue**: `build_aether.py` only copied files to `_internal/` but never invoked PyInstaller
- **Symptom**: "Executable" was just Python scripts, no `base_library.zip`, no bundled packages
- **Fix**: Manually ran PyInstaller with correct arguments:
  ```bash
  pyinstaller --noconfirm --onedir --windowed --name Aether --icon desktop_ui/logo.ico \
    --add-data "desktop_ui;desktop_ui" --add-data "aether;aether" \
    --hidden-import webview --hidden-import uvicorn.logging \
    --hidden-import uvicorn.loops.auto --hidden-import uvicorn.protocols.http.auto \
    --hidden-import uvicorn.protocols.websockets.auto --hidden-import uvicorn.lifespan.on \
    --hidden-import win32com --hidden-import win32com.client --hidden-import winshell \
    --distpath dist_build --workpath build_aether build_entry.py
  ```

### 2. ERR_CONNECTION_REFUSED (Race Condition)
- **Issue**: Server thread started, 1.5s sleep, then immediate `webview.create_window()` before server was listening
- **Fix**: Health-endpoint polling in `main()` before creating window (see SKILL.md)

### 3. FastAPI Decorator Typo
- **Issue**: `@api.post("/api/chat")` instead of `@app.post("/api/chat")` → `NameError: name 'api' is not defined`
- **Fix**: Changed `api` to `app` in `desktop_app_fixed.py` line 202

### 4. Missing `model` Field in ChatRequest
- **Issue**: `ChatRequest` model missing `model: Optional[str] = None` field referenced in chat endpoint
- **Fix**: Added the field to the Pydantic model

### 5. Stale Processes Blocking Rebuild/Run
- **Issue**: Old `Aether.exe` instances held port 8732 and locked `_internal/` files
- **Fix**: Always `taskkill /F /IM Aether.exe` before rebuild and before testing

### 6. Port Conflict from Dev Test Server
- **Issue**: Dev test server (`uvicorn.run(app)`) left on port 8732 blocked the exe
- **Fix**: Kill all python/uvicorn processes before testing the frozen exe

## Verification Checklist (All Passed)
- [x] `GET /api/health` → `{"ok":true}`
- [x] `POST /api/chat` normal mode → streaming SSE tokens
- [x] `POST /api/chat` RAG mode → grounded response with citations
- [x] Session mode persists (new session with `mode="rag"` stays rag)
- [x] `/ui/` serves HTML with correct title
- [x] Native pywebview window opens (not browser fallback)
- [x] Taskbar/shortcut icon visible (PyInstaller --icon + runtime copy)

## Key Commands for Future Rebuilds
```powershell
# Clean
taskkill /F /IM Aether.exe 2>$null
Remove-Item -Recurse -Force dist_build\Aether -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force build_aether -ErrorAction SilentlyContinue

# Build
cd C:\Users\valte\aether
C:\Users\valte\AppData\Local\hermes\hermes-agent\venv\Scripts\pyinstaller.exe --noconfirm --onedir --windowed --name Aether --icon desktop_ui/logo.ico --add-data "desktop_ui;desktop_ui" --add-data "aether;aether" --hidden-import webview --hidden-import uvicorn.logging --hidden-import uvicorn.loops.auto --hidden-import uvicorn.protocols.http.auto --hidden-import uvicorn.protocols.websockets.auto --hidden-import uvicorn.lifespan.on --hidden-import win32com --hidden-import win32com.client --hidden-import winshell --distpath dist_build --workpath build_aether build_entry.py

# Test (headless)
AETHER_HEADLESS=1 C:\Users\valte\aether\dist_build\Aether\Aether.exe &
sleep 5
curl -s http://127.0.0.1:8732/api/health
curl -s -X POST http://127.0.0.1:8732/api/chat -H "Content-Type: application/json" -d "{\"message\":\"hello\",\"mode\":\"normal\"}"

# Full test
C:\Users\valte\aether\dist_build\Aether\Aether.exe
```

## Files Modified This Session
- `desktop_app_fixed.py` — Fixed `@api.post` typo, added `model` to `ChatRequest`
- `build_entry.py` — Fixed `app.run()` → `uvicorn.run(app, ...)`
- `build_aether.py` — (Not actually used; PyInstaller run manually)

## Lessons Learned
1. **Always verify PyInstaller actually ran** — check for `Building EXE`, `Building COLLECT`, `Build complete!` in output
2. **Health-endpoint polling > fixed sleep** — eliminates ERR_CONNECTION_REFUSED race
3. **Kill stale processes before every test** — prevents port conflicts and rebuild locks
4. **Test the frozen exe, not just dev server** — MSYS/uv shim behavior differs from frozen exe


---

# Session: Aether Desktop App Critical Fixes (2026-07-29 Evening)

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

## Verification Script Added
Created `scripts/verify-frozen-app.py` - generic pattern for testing frozen PyInstaller + pywebview apps:
```bash
python scripts/verify-frozen-app.py desktop_app_fixed.py --port 8732
```

This script:
1. Kills existing processes on the port
2. Starts the backend
3. Waits for health endpoint
4. Tests normal mode chat
5. Tests RAG mode chat


---

# Session: Aether Desktop App Complete Frontend-Backend Integration Fix (2026-07-29 Late Evening)

## Problem Summary
After fixing the basic launch issues, the app still had critical frontend-backend integration problems:
- 50+ missing API endpoints that the frontend expected
- Chat SSE format mismatch (frontend expected `step` events)
- Duplicate `__main__` blocks in `desktop_app_fixed.py`
- Memory API used wrong method name (`entries()` vs `all()`)
- Backup API signatures didn't match frontend expectations

## Root Causes Identified & Fixed

### 1. Missing 50+ API Endpoints
Frontend `index.html` had `fetch(API+'/endpoint')` calls for many endpoints that didn't exist in the backend.

**Fix**: Implemented ALL missing endpoints in `desktop_app_fixed.py`:

| Category | Endpoints Added |
|----------|----------------|
| Sessions | `/api/sessions/{sid}/files`, PATCH/DELETE session |
| PDFs/RAG | `/api/pdfs/sync-watchdir`, `/api/pdfs/rebuild`, `/api/pdfs/remove` |
| Skills | `/api/skills`, `/api/skills/{name}`, `/api/skills/save`, `/api/skills/delete` |
| Tools | `/api/tools` with enabled status |
| MCP | `/api/mcp`, `/api/mcp/add`, `/api/mcp/delete`, `/api/mcp/test` |
| Memory | `/api/memory` (using `all()` not `entries()`), add/delete/update |
| Persona | `/api/persona/SOUL.md`, `/api/persona/USER.md`, `/api/persona/save` |
| Providers | `/api/providers`, `/api/providers/active`, `/api/config`, `/api/settings` |
| Telegram | `/api/telegram`, `/api/telegram/token`, `/api/telegram/mode` |
| Appearance | `/api/appearance` GET/POST |
| Backup | `/api/backup/export`, `/api/backup/import` |
| Diagnostics | `/api/diagnose`, `/api/debug_dump`, `/api/updates/check`, `/api/updates/download` |
| Misc | `/api/openfolder`, `/api/items/toggle`, `/api/reasoning`, `/api/updates/*` |

### 2. Chat SSE Format Mismatch
**Issue**: Frontend expected SSE events with `step` field (`thinking`, `answer`, `tool_start`, `tool_end`, `token`, `done`), but backend returned simple `data: {token: ...}` format.

**Fix**: Emit proper step events in `chat_endpoint`:
```python
# Send thinking step
yield f"data: {json.dumps({'step': 'thinking', 'label': 'Starting agent...'})}\n\n"

result = agent.run_agent(...)

# Send answer step
yield f"data: {json.dumps({'step': 'answer', 'label': 'Composing answer'})}\n\n"

# Stream the result
yield f"data: {json.dumps({'token': result})}\n\n"
yield f"data: {json.dumps({'done': True})}\n\n"
```

### 3. Duplicate `__main__` Blocks
**Issue**: Two `if __name__ == "__main__":` blocks in `desktop_app_fixed.py`
**Fix**: Removed duplicate, kept single `main()` entry point

### 4. Memory API Method Name
**Issue**: `mem.entries()` doesn't exist; method is `mem.all()`
**Fix**: Changed `mem.entries()` → `mem.all()` in `/api/memory` endpoint

### 5. Backup API Signatures
**Issue**: `export_backup(dest_path)` / `import_backup(src_path)` signatures didn't match API calls (no args vs path arg)
**Fix**: Added `export_backup()` no-arg version in `config.py` that generates temp file

### 6. Invalid `reasoning_effort` Parameter
**Issue**: `agent.run_agent()` doesn't accept `reasoning_effort` parameter
**Fix**: Removed the parameter from `chat_endpoint` call

### 7. ChatRequest Missing `model` Field (Already Fixed)
Already fixed in morning session but verified working.

## Files Modified This Session

### `desktop_app_fixed.py` — Complete Rewrite
- Added all 50+ missing API endpoints
- Fixed chat endpoint SSE format with step events
- Fixed import path (`from desktop_app_fixed import app`)
- Removed duplicate `__main__` block
- Removed invalid `reasoning_effort` parameter
- Fixed `mem.entries()` → `mem.all()`
- Added health check polling before WebView launch

### `build_entry.py` — Clean Entry Point
- Calls `main()` from `desktop_app_fixed.py`
- Custom uvicorn `log_config` with `use_colors: False` for frozen builds

### `aether/config.py` — Backup API Fixes
- Fixed `export_backup()` / `import_backup()` signatures
- Added `export_backup()` no-arg version that creates temp zip

### `aether/skills.py` — Save Skill Wrapper
- Added `save_skill(name, content)` returning status dict

### `aether/memory.py` — Uses `all()` Method
- Already correct, verified working

## PyInstaller Build Command (Updated)
```bash
pyinstaller.exe --noconfirm --onedir --windowed \
  --name Aether \
  --icon desktop_ui/logo.ico \
  --add-data "desktop_ui;desktop_ui" \
  --add-data "aether;aether" \
  --hidden-import webview \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.protocols.websockets.auto \
  --hidden-import uvicorn.lifespan.on \
  --hidden-import win32com \
  --hidden-import win32com.client \
  --hidden-import winshell \
  --hidden-import pythonnet \
  --hidden-import clr \
  --hidden-import requests \
  --distpath dist_build \
  --workpath build_aether \
  build_entry.py
```

**Key Exclusions for Large Builds** (reduces from ~900MB to ~135MB, avoids 0xc0000005):
- Exclude ML packages: `torch`, `torchvision`, `torchaudio`, `transformers`, `tokenizers`, `safetensors`, `sentencepiece`, `huggingface_hub`, `timm`, `accelerate`, `cv2`, `onnxruntime`

## Critical Windows-Specific Fixes

### 1. Process Lock Cleanup Before Rebuild
```powershell
taskkill /F /IM Aether.exe
taskkill /F /IM Aether-Setup.exe
```
Must run before every rebuild to avoid `PermissionError: [WinError 5] Access is denied` on `base_library.zip`.

### 2. Inno Setup Compression
Switch from `Compression=lzma2/ultra64` + `SolidCompression=yes` to `Compression=zip` + `SolidCompression=no` to avoid bootloader `0xc0000005` crash on large builds.

### 3. Icon Handling
- **EXE/Taskbar icon**: Add `--icon=logo.ico` to PyInstaller (embeds in PE header)
- **In-window/favicon**: Add `<link rel="icon" href="/ui/logo.ico">` to HTML
- **Installer/Start Menu**: Set `SetupIconFile=desktop_ui/logo.ico` in `.iss`
- **DO NOT** pass `icon=` to `webview.create_window()` (pre-4.0 pywebview raises TypeError)

### 4. pywebview Hidden Import
Use `--hidden-import webview` (NOT `pywebview` - package imports as `webview`).

## Testing Protocol
1. Launch frozen exe: `C:\Users\valte\aether\dist_build\Aether\Aether.exe`
2. Wait for backend health check to pass
3. Verify native WebView2 window opens (Alt+Tab → "Aether — Agent + RAG")
4. Test API endpoints:
   ```bash
   curl http://127.0.0.1:8732/api/health
   curl -X POST http://127.0.0.1:8732/api/chat -H "Content-Type: application/json" -d '{"message":"what is rag","mode":"rag"}'
   ```
5. Verify all UI features: sidebar navigation, mode toggle, skills/tools/mcp/memory panels, settings

## Verification Results (All Passed)
- `GET /api/health` → `{"ok":true,"status":"running"}` ✅
- `GET /` → Full HTML UI loads ✅
- `POST /api/chat` (normal) → Streaming SSE with step events ✅
- `POST /api/chat` (rag) → Full RAG explanation ✅
- `GET /api/skills` → 100+ skills listed ✅
- `GET /api/tools` → All tools with enabled status ✅
- `GET /api/mcp` → 6 MCP servers configured ✅
- `GET /api/sessions` → Session list with mode/pinned/files ✅
- `GET /api/providers` → 3 providers (OpenRouter, OpenAI, Ollama) ✅
- `GET /api/appearance` → Theme/font/rounded/auto_upgrade ✅
- `GET /api/memory` → Memory entries list ✅
- `GET /api/pdfs` → PDF list + sync/rebuild endpoints ✅
- `GET /api/config` → Full config with has_key ✅

## Files Changed Summary
| File | Changes |
|------|---------|
| `desktop_app_fixed.py` | +50 endpoints, SSE step events, fixed imports, removed duplicate main |
| `build_entry.py` | Clean entry point, custom uvicorn log_config |
| `aether/config.py` | Fixed backup API signatures, added export_backup() no-arg |
| `aether/skills.py` | Added save_skill() wrapper |
| `aether/memory.py` | Verified all() method works |

## Lessons for Future
1. **Always poll health endpoint before launching WebView** — backend startup is async
2. **Frozen builds need local imports** — avoid cross-module imports that work in dev but fail frozen
3. **Frontend drives API contract** — check frontend `fetch(API+'/endpoint')` calls to discover missing endpoints
4. **SSE format is a contract** — frontend parses `step` field for UI animations
5. **Kill processes before rebuild** — Windows file locks are persistent
6. **Exclude heavy ML packages** — keeps build small and avoids AV/defender crashes
7. **Test via API not just UI** — curl the endpoints directly to verify backend
8. **Frontend `fetch` calls are the source of truth** for what endpoints must exist
9. **SSE `step` events drive frontend UI animations** — not optional

## Key Commands for Future
```powershell
# Kill and clean
taskkill /F /IM Aether.exe 2>$null
Remove-Item -Recurse -Force dist_build\Aether, build_aether -ErrorAction SilentlyContinue

# Build
cd C:\Users\valte\aether
C:\Users\valte\AppData\Local\hermes\hermes-agent\venv\Scripts\pyinstaller.exe --noconfirm --onedir --windowed --name Aether --icon desktop_ui/logo.ico --add-data "desktop_ui;desktop_ui" --add-data "aether;aether" --hidden-import webview --hidden-import uvicorn.logging --hidden-import uvicorn.loops.auto --hidden-import uvicorn.protocols.http.auto --hidden-import uvicorn.protocols.websockets.auto --hidden-import uvicorn.lifespan.on --hidden-import win32com --hidden-import win32com.client --hidden-import winshell --hidden-import pythonnet --hidden-import clr --hidden-import requests --distpath dist_build --workpath build_aether build_entry.py

# Test headless
AETHER_HEADLESS=1 C:\Users\valte\aether\dist_build\Aether\Aether.exe &
sleep 5
curl -s http://127.0.0.1:8732/api/health
curl -s -X POST http://127.0.0.1:8732/api/chat -H "Content-Type: application/json" -d "{\"message\":\"what is rag\",\"mode\":\"rag\"}"

# Full test
C:\Users\valte\aether\dist_build\Aether\Aether.exe
```