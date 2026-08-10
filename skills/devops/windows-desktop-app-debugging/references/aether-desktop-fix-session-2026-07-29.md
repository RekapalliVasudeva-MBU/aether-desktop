# Aether Desktop Fix Session - 2026-07-29

## Session Context
User reported: "the app is opening but nothing is working inside" - ERR_CONNECTION_REFUSED on 127.0.0.1:8732, multiple backend bugs.

## Root Causes Found & Fixed

### 1. ERR_CONNECTION_REFUSED (Primary Issue)
**Cause:** Backend FastAPI server not actually starting in frozen exe
**Fix:** 
- Fixed `build_entry.py` - `app.run()` → `uvicorn.run(app, ...)`
- Fixed `desktop_app_fixed.py` - `@api.post` typo → `@app.post`
- Added missing `model` field to `ChatRequest` Pydantic model
- Health endpoint polling in `main()` before creating WebView2 window

### 2. Multiple Backend Bugs
| Bug | Location | Fix |
|-----|----------|-----|
| `UnboundLocalError: _webview2_installed` | `desktop_app_fixed.py` line 202 | Function definition order |
| `TypeError: bad operand type for unary -: 'WindowsPath'` | Session sorting | `reverse=True` instead of `-path.stat().st_mtime` |
| `JSONDecodeError: Invalid \escape` | File upload | Windows path escaping in JSON |
| `KeyError: 'pinned'` | Session loading | Default `pinned: False` in session dict |
| MCP connection spam | `aether/agent.py` | Only connect configured servers + 60s cache |

### 3. Build Script Not Running PyInstaller
**Critical discovery:** `build_aether.py` only copied files to `_internal/` but NEVER invoked PyInstaller. The "executable" was just a Python script that wouldn't run without the full venv.

**Fix:** Ran PyInstaller manually with correct flags:
```cmd
pyinstaller --noconfirm --onedir --windowed --name Aether --icon desktop_ui/logo.ico --add-data "desktop_ui;desktop_ui" --add-data "aether;aether" --hidden-import webview --hidden-import uvicorn.logging --hidden-import uvicorn.loops.auto --hidden-import uvicorn.protocols.http.auto --hidden-import uvicorn.protocols.websockets.auto --hidden-import uvicorn.lifespan.on --hidden-import win32com --hidden-import win32com.client --hidden-import winshell --distpath dist_build --workpath build_aether build_entry.py
```

## Verification Results (All Passed)
- ✅ `GET /api/health` → `{"ok":true}`
- ✅ `POST /api/chat` normal mode → streaming SSE tokens
- ✅ `POST /api/chat` RAG mode → grounded response with citations
- ✅ Session mode persistence works
- ✅ Native pywebview window opens (no browser fallback)
- ✅ Taskbar/shortcut icon visible

## PowerShell Rescue Commands (Copy-Paste Ready)

### Clean & Rebuild
```powershell
# Kill stale processes
taskkill /F /IM Aether.exe 2>$null
taskkill /F /IM python.exe 2>$null
taskkill /F /IM uvicorn.exe 2>$null

# Clean build artifacts
Remove-Item -Recurse -Force dist_build\Aether -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force build_aether -ErrorAction SilentlyContinue

# Build
cd C:\Users\valte\aether
C:\Users\valte\AppData\Local\hermes\hermes-agent\venv\Scripts\pyinstaller.exe --noconfirm --onedir --windowed --name Aether --icon desktop_ui/logo.ico --add-data "desktop_ui;desktop_ui" --add-data "aether;aether" --hidden-import webview --hidden-import uvicorn.logging --hidden-import uvicorn.loops.auto --hidden-import uvicorn.protocols.http.auto --hidden-import uvicorn.protocols.websockets.auto --hidden-import uvicorn.lifespan.on --hidden-import win32com --hidden-import win32com.client --hidden-import winshell --distpath dist_build --workpath build_aether build_entry.py
```

### Test Frozen Exe (Headless)
```powershell
# Start frozen exe headless
$env:AETHER_HEADLESS=1
Start-Process -FilePath "C:\Users\valte\aether\dist_build\Aether\Aether.exe" -NoNewWindow
Start-Sleep 5

# Test endpoints
curl -s http://127.0.0.1:8732/api/health
curl -s -X POST http://127.0.0.1:8732/api/chat -H "Content-Type: application/json" -d '{"message":"hello","mode":"normal"}'
```

### Full GUI Test
```powershell
C:\Users\valte\aether\dist_build\Aether\Aether.exe
```

## Files Modified This Session
- `C:\Users\valte\aether\desktop_app_fixed.py` — Fixed `@api.post` typo, added `model` field
- `C:\Users\valte\aether\build_entry.py` — Fixed `app.run()` → `uvicorn.run()`

## Key Lessons
1. **Always verify PyInstaller output** - Check for "Building EXE", "Building COLLECT", "Build complete!" messages
2. **Health polling > fixed sleep** - Eliminates ERR_CONNECTION_REFUSED race
3. **Kill stale processes before every test** - Prevents port conflicts and rebuild locks
4. **Test frozen exe, not dev server** - MSYS/uv shim behavior differs from frozen Windows python
5. **User was right to be frustrated** - Multiple compounding bugs, not a single issue