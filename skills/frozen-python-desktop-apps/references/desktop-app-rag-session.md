# Aether Desktop + RAG Session Log (2026-07-26)

## Problem: RAG mode not saved in new sessions

### Issue
When creating a new session via the desktop app, the RAG/Normal mode toggle was not persisted. The `/api/sessions/new` endpoint always defaulted to `"mode": "normal"` even when the user was in RAG mode.

### Root Cause
`desktop_app.py` line 294 hardcoded `"mode": "normal"` when creating new sessions. The frontend `newSession()` function did not pass the current mode to the API.

### Fix (2 files)
1. **`desktop_app.py`** `api_session_new()` — read `mode` from request body, default to `"normal"`
2. **`desktop_ui/index.html`** `newSession()` — send `{mode}` in POST body with `Content-Type: application/json`

### Verification
```bash
# Create RAG session
curl -s -X POST http://localhost:8732/api/sessions/new -H "Content-Type: application/json" -d '{"mode": "rag"}'
# Returns: {"id":"chat_xxx"}
# Check session file contains "mode": "rag"
```

### Pitfall
The session file on disk uses `json.dumps(data, ensure_ascii=False)` — mode field must be in the dict passed to `_save_session`. The `_load_session` fallback also defaults to `"normal"` which is correct for new sessions without mode field.