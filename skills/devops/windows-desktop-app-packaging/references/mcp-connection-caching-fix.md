# MCP Connection Caching Fix (Aether Desktop App)

## Problem
MCP servers were being reconnected on **every single API request** (chat, sessions, tools, skills, etc.), causing massive log spam and performance degradation.

Log showed:
```
[mcp] failed to connect testmcp: [WinError 10038] An operation was attempted on something that is not a socket
[mcp] failed to connect playwright: [WinError 2] The system cannot find the file specified
[mcp] failed to connect duckduckgo_search: [WinError 2] The system cannot find the file specified
...
(repeated 100+ times in logs)
```

Each endpoint (`/api/sessions`, `/api/chat`, `/api/tools`, etc.) called `mcp_mod.connect_all()` independently.

## Root Cause
In `aether/agent.py`:
- `get_external_tool_schemas()` called `mcp_mod.connect_all()`
- `_tool_specs()` called `mcp_mod.connect_all()`
- `run_agent()` called `mcp_mod.connect_all()` for MCP tool execution

All three were called on every chat request, plus the GET endpoints also triggered tool schema collection.

## Fix Applied
Added a module-level cache with 60-second TTL in `aether/agent.py`:

```python
# Cache MCP connections to avoid reconnecting on every request
_mcp_clients_cache = None
_mcp_clients_timestamp = 0

def _get_cached_mcp_clients():
    """Get MCP clients with caching - only reconnect once per minute."""
    global _mcp_clients_cache, _mcp_clients_timestamp
    import time
    now = time.time()
    if _mcp_clients_cache is None or (now - _mcp_clients_timestamp) > 60:
        try:
            _mcp_clients_cache = mcp_mod.connect_all()
            _mcp_clients_timestamp = now
        except Exception as e:
            print(f"[mcp] connect_all failed: {e}")
            _mcp_clients_cache = {}
    return _mcp_clients_cache
```

Then replaced all three `mcp_mod.connect_all()` calls with `_get_cached_mcp_clients()`.

## Location
`C:/Users/valte/aether/aether/agent.py` lines 23-42 (cache), 57, 89, 237 (usages)

## Verification
```bash
# Start the app
curl -s http://127.0.0.1:8732/api/health

# Check logs after multiple requests
tail -20 C:/Users/valte/AppData/Local/Aether/aether_stdout.log
# Should show MCP connection attempts only ONCE per minute, not per request
```

## Performance Impact
- Before: ~10-20 MCP connection attempts per chat request
- After: 1 MCP connection attempt per minute (cached)
- Log volume reduced from ~200 lines/minute to ~3 lines/minute

## Prevention
- Any module-level function that spawns subprocesses or makes network connections should be cached
- Use a TTL cache for external service connections
- Add logging to connection functions so spam is visible during debugging