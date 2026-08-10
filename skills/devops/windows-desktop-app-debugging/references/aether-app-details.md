# Aether App - Session Specific Details

## App Locations
- **Source**: `C:\Users\valte\aether\`
- **Installed exe**: `C:\Users\valte\AppData\Local\Aether\Aether.exe`
- **Frozen resources**: `C:\Users\valte\AppData\Local\Aether\_internal\`
- **Desktop UI (runs)**: `C:\Users\valte\AppData\Local\Aether\_internal\desktop_ui\index.html`
- **Logs**: `C:\Users\valte\AppData\Local\Aether\aether_stdout.log`, `aether_startup.log`, `aether_launch.log`

## Fixed Issues (This Session)
1. **Splash animation blocking UI** - Patched installed `_internal/desktop_ui/index.html`:
   - Removed `<div id="splash">` HTML block
   - Removed splash CSS (`#splash`, `.logo-spin`, `@keyframes pulse`, `@keyframes load`, `.bar`)
   - Removed splash JS (900ms setTimeout + 3s fallback)

2. **Backend API verified working** - RAG mode returns citations from indexed PDFs via:
   ```bash
   curl -X POST http://127.0.0.1:8732/api/chat \
     -H "Content-Type: application/json" \
     -d "{\"mode\":\"rag\",\"message\":\"what is rag\",\"session_id\":null}"
   ```

## Session 2026-07-29: Critical Frozen Bugs Identified & Fixed
From `aether_stdout.log` analysis, the frozen app has these **source-level bugs** that require rebuild:

| Bug | Location | Error | Fix Applied |
|-----|----------|-------|-------------|
| `_webview2_installed` UnboundLocalError | `desktop_app.py` line ~1380 | Function defined inside `if` block, called at module level | Created `desktop_app_impl.py` with function at module level |
| Session sort TypeError | `desktop_app.py` line 96 | `lambda` uses Path object with unary `-` | Changed to `key=lambda p: p.stat().st_mtime, reverse=True` |
| JSON decode on Windows paths | `desktop_app.py` line 316 | `request.json()` fails on `\` in file paths | Proper path escaping in file upload handling |
| `api_session_patch` KeyError | `desktop_app.py` line 324 | Missing 'pinned' field in session | Added default `pinned: False` in session creation |

### MCP Connection Spam (Fixed in New Implementation)
The app was repeatedly trying to connect to non-existent MCP servers:
- `testmcp` - `[WinError 10038] operation attempted on something that is not a socket`
- `playwright` - `[WinError 2] The system cannot find the file specified`
- `duckduckgo_search`, `ddg`, `youtube-mcp`, `filesystem-mcp` - same file not found errors

**Fix**: New `desktop_app_impl.py` only attempts MCP connections for servers explicitly configured and enabled in config.yaml, with 60-second caching.

## Files Created/Updated This Session

### `C:\Users\valte\aether\desktop_app_impl.py` (NEW - Complete Implementation)
Full FastAPI + WebView2 backend with:
- All API endpoints: chat, sessions, PDFs/RAG, skills, tools, MCP, memory, persona, providers, telegram, appearance, backup
- Proper singleton lock preventing multiple instances
- WebView2 detection via EdgeUpdate registry key + silent installer fallback
- MCP client caching (60s TTL) to avoid connection spam
- Fixed WindowsPath sorting, JSON path escaping, session pinned defaults
- Clean shutdown via `/api/shutdown` endpoint

### `C:\Users\valte\aether\build_aether.py` (UPDATED)
Added `--add-data` for `aether` package so source modules are included in frozen build.

## Build Configuration
- **Build script**: `C:\Users\valte\aether\build_aether.py`
- **Entry point**: `C:\Users\valte\aether\build_entry.py` → imports `desktop_app_impl.main`
- **PyInstaller**: `--onedir --windowed` (not --onefile to avoid AV triggers)
- **Icon**: `C:\Users\valte\aether\desktop_ui\logo.ico`
- **Data files**: `desktop_ui` folder, `aether` package, `chromadb_pkg` bundled

## Build Failure (Current)
```
PermissionError: [WinError 32] The process cannot access the file because it is being used by another process: 'C:\Users\valte\aether\dist_build\Aether'
```
Fix: Kill all Aether/WebView2 processes, then `rmdir /s /q dist_build build_aether` before rebuild.

## Test Commands
```cmd
REM Kill and launch installed app
taskkill /F /IM Aether.exe 2>nul
"C:\Users\valte\AppData\Local\Aether\Aether.exe"

REM Test RAG API
curl -X POST http://127.0.0.1:8732/api/chat -H "Content-Type: application/json" -d "{\"mode\":\"rag\",\"message\":\"what is rag\",\"session_id\":null}"
```

## Environment
- Windows 10/11
- Python 3.11.15 (uv managed)
- WebView2 Runtime: detected via EdgeUpdate registry key
- Ollama local: `qwythos-9b-abliterated:Q4_K_M`
- OpenRouter: free models only (`:free`)