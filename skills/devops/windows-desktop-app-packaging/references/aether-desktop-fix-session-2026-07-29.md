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
- [ ] `GET /api/health` → `{"ok":true}`
- [ ] `POST /api/chat` normal mode → streaming SSE tokens
- [ ] `POST /api/chat` RAG mode → grounded response with citations
- [ ] Session mode persists (new session with `mode="rag"` stays rag)
- [ ] `/ui/` serves HTML with correct title
- [ ] Native pywebview window opens (not browser fallback)
- [ ] Taskbar/shortcut icon visible (PyInstaller --icon + runtime copy)

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