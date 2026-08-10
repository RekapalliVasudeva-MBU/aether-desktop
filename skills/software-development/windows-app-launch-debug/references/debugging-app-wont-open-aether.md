# Debugging "App Won't Open" for Aether Desktop (PyInstaller + pywebview + FastAPI)

## Context
User reported: "app is just loading not opening see what happened and fix this permanently ok its opening and loading continuously and not showing the chat etc all things inside its keep on loading"

## Root Cause Identified
Two bugs in the frozen app:

### Bug 1: Session List Sorting Crash
- **Endpoint**: `/api/sessions` 
- **Error**: `TypeError: bad operand type for unary -: 'WindowsPath'`
- **Location**: `desktop_app.py:96` in `_list_sessions()` → `_mtime()` helper
- **Root Cause**: `_mtime()` returned a `Path` object instead of a float timestamp
- **Fix**: Return `float(p.stat().st_mtime)` with explicit type annotation

### Bug 2: MCP Connection Spam
- **Symptom**: 100+ log lines per minute of `[mcp] failed to connect...`
- **Root Cause**: `mcp_mod.connect_all()` called on every API request (3 places in `agent.py`)
- **Fix**: Added module-level cache with 60-second TTL in `agent.py`

## Debugging Process Used

### Step 1: Kill stale processes
```bash
taskkill /F /IM Aether.exe
```

### Step 2: Test dev version first (faster iteration)
```bash
cd C:/Users/valte/aether
python desktop_app.py
# Wait for "server ready" message
```

### Step 3: Test API endpoints directly
```bash
curl -s http://127.0.0.1:8732/api/health
curl -s http://127.0.0.1:8732/api/sessions
```

### Step 4: Check logs for errors
```bash
tail -50 C:/Users/valte/AppData/Local/Aether/aether_stdout.log
```

### Step 5: Apply fixes to source files
- Patch `desktop_app.py` - fix `_mtime()` function
- Patch `aether/agent.py` - add MCP connection caching

### Step 6: Rebuild frozen exe
```bash
python build_aether.py
```

### Step 7: Test frozen exe with AETHER_HEADLESS
```bash
taskkill /F /IM Aether.exe 2>/dev/null
AETHER_HEADLESS=1 terminal(background=true, command="dist_build/Aether/Aether.exe")
sleep 10
curl -s http://127.0.0.1:8732/api/health
curl -s http://127.0.0.1:8732/api/sessions
```

### Step 8: Full functional verification
```bash
# Normal chat
curl -X POST http://127.0.0.1:8732/api/chat -H "Content-Type: application/json" -d '{"mode":"normal","message":"hi","session_id":"t1"}'

# RAG chat with session mode persistence
curl -X POST http://127.0.0.1:8732/api/sessions/new -H "Content-Type: application/json" -d '{"mode":"rag"}'
curl -X POST http://127.0.0.1:8732/api/chat -H "Content-Type: application/json" -d '{"mode":"rag","message":"What is RAG?","session_id":"<id>"}'
```

## Key Debugging Patterns for This App Type

1. **Always test the FROZEN exe, not the dev server** - PyInstaller changes import paths, stdout handling, and WebView2 initialization
2. **Use AETHER_HEADLESS=1 for API testing** - bypasses WebView2 window, keeps server running
3. **Check aether_stdout.log for frozen exe errors** - the log captures stdout/stderr from the frozen process
4. **Kill stale instances before each test** - orphaned processes hold the port and mutex
5. **Use `timeout 15` returning 124 as SUCCESS** - means the process was alive and timeout killed it

## Files Modified
- `C:/Users/valte/aether/desktop_app.py` lines 101-107
- `C:/Users/valte/aether/aether/agent.py` lines 23-42, 57, 89, 237

## Verification Results
✅ Session list returns sorted JSON (no crash)
✅ Normal chat works with SSE streaming
✅ RAG chat works with citations
✅ Session mode (normal/rag) persists correctly
✅ MCP logs reduced from 100+/min to ~3/min
✅ UI loads at /ui/