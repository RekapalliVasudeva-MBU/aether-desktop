# Aether v1.3.1 RAG Mode Session Persistence Fix

## Problem
New chat sessions created in RAG mode were not persisting the mode - they defaulted to "normal" mode. The session mode was only saved when the first message was sent, not when the session was created.

## Root Cause
1. Backend `/api/sessions/new` always created sessions with `"mode": "normal"` regardless of current UI mode
2. Frontend `newSession()` didn't send the current `mode` variable to the backend
3. `_load_session()` didn't provide defaults for `mode` and `pinned` fields

## Solution (3 Files Changed)

### 1. `desktop_app.py` - `/api/sessions/new` endpoint (line 293-305)
```python
@app.post("/api/sessions/new")
async def api_session_new(req: Request = None):
    import uuid
    mode = "normal"
    if req:
        try:
            body = await req.json()
            mode = body.get("mode", "normal")
        except Exception:
            pass
    sid = f"chat_{uuid.uuid4().hex[:10]}"
    _save_session(sid, {"id": sid, "title": "(new chat)", "messages": [], "mode": mode})
    return JSONResponse({"id": sid})
```

### 2. `desktop_app.py` - `_load_session()` (line 57-68)
```python
def _load_session(sid: str) -> Dict:
    p = _session_file(sid)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            data.setdefault("pinned", False)
            data.setdefault("mode", "normal")
            return data
        except Exception:
            pass
    return {"id": sid, "title": "(new chat)", "messages": [], "mode": "normal", "pinned": False}
```

### 3. `desktop_ui/index.html` - `newSession()` function (line 391-395)
```javascript
async function newSession(){
  const r = await fetch(API+'/api/sessions/new',{method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({mode})}); const d = await r.json();
  sessionId = d.id; const m=document.getElementById('messages'); if(m) m.innerHTML='';
  await loadSessionList();
}
```

## Verification
- Created session with `{"mode": "rag"}` → session file has `"mode": "rag"`
- Session endpoint returns mode correctly
- Sessions list includes mode for all sessions
- Rebuild required (PyInstaller frozen app)

## Related
- `references/aether_v1.3.0_sessions.md` - Session panel redesign
- `references/pywebview_desktop_app.md` - Desktop app architecture