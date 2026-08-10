# Aether App Debugging Session — 2026-07-28

## Problem Summary
Aether desktop app (PyWebView + FastAPI + PyInstaller) showed only splash animation, no chat UI. Backend API worked but frozen executable had multiple bugs.

## Root Causes Found

### 1. Splash Animation Blocking UI
**File:** `C:\Users\valte\AppData\Local\Aether\_internal\desktop_ui\index.html`
- Splash div, CSS animations, and JS timeouts prevented chat UI from rendering
- **Fix:** Removed splash div, splash HTML div, splash CSS (#splash, .logo-spin, @keyframes pulse/load), splash JS (setTimeout hide + 3s fallback)

### 2. Frozen Python Bugs (in compiled exe, require rebuild)
From `aether_stdout.log`:
- `_webview2_installed` UnboundLocalError: function defined inside `if` block, called at module level
- Session sort TypeError: `bad operand type for unary -: 'WindowsPath'` in `_list_sessions` lambda
- JSON decode error: Windows paths with `\` break `request.json()` in `api_session_add_file`
- KeyError 'pinned' in `api_session_patch`

### 3. PyInstaller Rebuild Blocked by File Locks
WebView2 spawns child processes (GPU, utility) that hold handles to `dist_build/Aether` even after main process dies.

## Fixes Applied

### Immediate (patch installed app)
1. Removed splash from `C:\Users\valte\AppData\Local\Aether\_internal\desktop_ui\index.html`
2. Verified backend API works: `curl -X POST http://localhost:8732/api/chat` returns RAG answers with citations

### Permanent (requires rebuild)
1. Fix `_webview2_installed` scope in `desktop_app.py` (move function outside `if` block)
2. Fix session sort: use `f.stat().st_mtime` instead of unary `-` on Path
3. Fix JSON decode: use `await request.json()` with proper path escaping
4. Fix `pinned` KeyError: provide default in session model

### Build Unblocking
```powershell
# Find openfiles locking the build dir
$open = cmd /c 'openfiles /query /fo csv /v 2>$null' | ConvertFrom-Csv 2>$null
$matches = $open | Where-Object { $_.'Open File Path' -like "*dist_build\Aether*" }
foreach ($m in $matches) { Stop-Process -Id $m.'Process ID' -Force }

# Kill WebView2 child processes
Get-Process -Name "*webview*","*msedgewebview2*","*Aether*" -ErrorAction SilentlyContinue | Stop-Process -Force

# Force unlock
cmd /c "takeown /f 'C:\Users\valte\aether\dist_build\Aether' /r /d y 2>$null"
cmd /c "icacls 'C:\Users\valte\aether\dist_build\Aether' /grant administrators:F /t /c /q 2>$null"

Remove-Item "C:\Users\valte\aether\dist_build\Aether" -Recurse -Force
```

## Verification
- Backend API: `curl -X POST http://localhost:8732/api/chat -d '{"mode":"rag","message":"what is rag"}'` → Returns answer with citations
- UI: `curl http://localhost:8732/ui/` → Serves index.html with chat-wrap, messages, composer elements
- No splash animation blocks chat view

## Additional Findings (2026-07-28 continuation)

### Frozen App Launch Failures
- App starts backend ("server ready at attempt 1") but crashes due to `_webview2_installed` UnboundLocalError
- Multiple "stale/dead instance" mutex messages indicate zombie processes
- MCP connection spam (playwright, duckduckgo, youtube, filesystem) - missing npm packages

### MCP Spam Issue
The frozen app tries to connect to MCP servers that aren't installed:
- `testmcp`, `playwright`, `duckduckgo_search`, `ddg`, `youtube-mcp`, `filesystem-mcp`
- These are npm packages that need `npm install -g @playwright/mcp@latest` etc.
- Not critical for core functionality but fills logs

### File Lock Resolution
After multiple attempts, the build directory lock was only cleared by:
1. Restarting Windows (releases all handles)
2. Then `rmdir /s /q dist_build build_aether` works cleanly

### Source vs Installed App
- **Source HTML:** `C:\Users\valte\aether\desktop_ui\index.html` (for next build)
- **Installed HTML:** `C:\Users\valte\AppData\Local\Aether\_internal\desktop_ui\index.html` (what actually runs)
- Both must be patched for immediate + permanent fix

## Notes for Next Rebuild
- Source HTML fix in `C:\Users\valte\aether\desktop_ui\index.html` will be included
- Frozen Python bugs require editing `desktop_app.py` before rebuild:
  1. Move `_webview2_installed` function to module level (outside `if` block)
  2. Fix session sort: `key=lambda f: f.stat().st_mtime` instead of unary `-`
  3. Fix JSON decode: parse Windows paths properly in `api_session_add_file`
  4. Fix `pinned` KeyError: use `.get('pinned', False)` in session model
- Build dirs: `dist_build/`, `build_aether/` must be clean before `python build_aether.py`
- Run `python make_installer.py` after build for Aether-Setup.exe