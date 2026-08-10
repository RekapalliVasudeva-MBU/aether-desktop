# Session Mode Persistence Fix (Aether Desktop App)

## Problem
When users created a new chat session in RAG mode, the session was saved with `mode: "normal"` instead of `mode: "rag"`. This meant switching back to that session would lose the RAG context and fall back to normal chat mode.

## Root Cause
The `/api/sessions/new` endpoint in `desktop_app.py` hardcoded `"mode": "normal"` when creating new sessions, ignoring the current UI mode (RAG/Normal) that the user had selected.

## Fix Applied

### Backend (`desktop_app.py`)
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

### Frontend (`desktop_ui/index.html`)
```javascript
async function newSession(){
  const r = await fetch(API+'/api/sessions/new',{
    method:'POST', 
    headers:{'Content-Type':'application/json'}, 
    body:JSON.stringify({mode})
  }); 
  const d = await r.json();
  sessionId = d.id; 
  const m=document.getElementById('messages'); if(m) m.innerHTML='';
  await loadSessionList();
}
```

The frontend now passes the current `mode` variable (which tracks whether the user is in "normal" or "rag" mode) when creating a new session.

## Verification
- Created new session in RAG mode → session file shows `"mode": "rag"`
- Created new session in Normal mode → session file shows `"mode": "normal"`
- Session list API returns correct mode for each session
- Loading a RAG session restores RAG context correctly

## Files Changed
- `C:/Users/valte/aether/desktop_app.py` (line ~293)
- `C:/Users/valte/aether/desktop_ui/index.html` (line ~392)

## Prevention
- Always pass the current UI state when creating resources that need to preserve that state
- Don't hardcode defaults for user-facing modes that can be toggled
- Test both modes when adding session-related features