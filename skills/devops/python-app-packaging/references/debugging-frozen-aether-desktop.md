# Debugging Frozen Aether Desktop App (PyInstaller + pywebview)

## Context
User reported the Aether desktop app "keep on loading" - the window opens but the UI never renders properly, showing a continuous loading state.

## Root Causes Found

### 1. Session List API Crash (`TypeError: bad operand type for unary -: 'WindowsPath'`)
- **File**: `desktop_app.py` → `_list_sessions()` → `_mtime()` helper
- **Issue**: `_mtime()` returned a `Path` object instead of float timestamp
- **Impact**: `/api/sessions` endpoint crashes, breaking sidebar session list
- **Fix**: Return `float(p.stat().st_mtime)` with type annotation

### 2. MCP Connection Storm (Log Spam + Performance)
- **File**: `aether/agent.py` - three calls to `mcp_mod.connect_all()` per request
- **Issue**: Every API call (`/api/sessions`, `/api/chat`, `/api/tools`, etc.) spawned MCP subprocesses
- **Impact**: 100+ log lines/minute, significant latency
- **Fix**: Module-level cache with 60-second TTL (`_get_cached_mcp_clients()`)

## Debugging Workflow for Frozen PyInstaller Apps

### Prerequisite: Clean Environment
```bash
# ALWAYS kill stale instances first
taskkill /F /IM Aether.exe 2>/dev/null

# Check no orphans holding port
netstat -ano | findstr :8732
```

### Dev-Server Iteration (Fast Feedback)
```bash
cd C:/Users/valte/aether
python desktop_app.py
# Wait for "server ready at attempt X"
```

### API Testing (Bypass WebView2)
```bash
# Use headless mode for API verification
AETHER_HEADLESS=1 python desktop_app.py &
sleep 10

curl -s http://127.0.0.1:8732/api/health
curl -s http://127.0.0.1:8732/api/sessions
```

### Frozen EXE Verification (The Real Test)
```bash
# Build
python build_aether.py

# Launch frozen exe headless
taskkill /F /IM Aether.exe 2>/dev/null
AETHER_HEADLESS=1 terminal(background=true, command="dist_build/Aether/Aether.exe")
sleep 10

# Test all endpoints
curl -s http://127.0.0.1:8732/api/health
curl -s http://127.0.0.1:8732/api/sessions
curl -s -X POST http://127.0.0.1:8732/api/chat -H "Content-Type: application/json" -d '{"mode":"normal","message":"hi","session_id":"t1"}'
```

### Log Analysis (Critical for Frozen Apps)
```bash
# Frozen exe logs to AppData
tail -50 C:/Users/valte/AppData/Local/Aether/aether_stdout.log

# Look for:
# - "server ready" → server started
# - "WebView2 found" → runtime OK
# - "[mcp] failed to connect" → MCP issues
# - Tracebacks → Python errors in frozen env
```

## Key Differences: Dev vs Frozen
| Aspect | Dev (`python desktop_app.py`) | Frozen (`Aether.exe`) |
|--------|-------------------------------|----------------------|
| Stdout | Visible in terminal | Redirected to `aether_stdout.log` |
| Import paths | Project source | `_internal/` + `base_library.zip` |
| WebView2 | System runtime | System runtime (same) |
| UI assets | `./desktop_ui/` | `_internal/desktop_ui/` |
| Current dir | Project root | `sys.executable` parent |

## Common Frozen-App Pitfalls
1. **`sys`/`os`/`Path` not imported** - used in module-level code for path resolution
2. **`webview.create_window(icon=...)` kwarg not supported** - older pywebview lacks it
3. **Missing DLLs** - PyInstaller `--hidden-import` or `--add-data` gaps
4. **Mutex/single-instance bugs** - orphaned processes block new launches
5. **ERR_CONNECTION_REFUSED** - server not ready when WebView2 navigates

## Files Modified in This Session
- `desktop_app.py`: Fixed `_mtime()` helper (lines 101-107)
- `aether/agent.py`: Added MCP connection caching (lines 23-42, usages at 57, 89, 237)

## Verification Checklist
- [ ] `/api/health` returns 200
- [ ] `/api/sessions` returns sorted JSON (no crash)
- [ ] `/api/chat` normal mode streams SSE
- [ ] `/api/chat` RAG mode returns citations
- [ ] Session mode persists (new session with `mode="rag"` stays rag)
- [ ] MCP logs ~3/min (not 100+/min)
- [ ] `/ui/` serves HTML with correct title

## References
- `references/session-list-sorting-bug-fix.md`
- `references/mcp-connection-caching-fix.md`
- `references/rebuilt-exe-verification.md`