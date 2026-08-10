# Aether Desktop App - RAG Mode Session Persistence Fix

Session from 2026-07-26: Fixed new chat sessions not preserving RAG/Normal mode.

## Problem
When creating a new chat session in the Aether desktop app via the **+ New chat** button or by starting to type in a fresh session, the mode (RAG vs Normal) was not being saved with the session. This meant:
1. User switches to RAG mode in the UI
2. Clicks + New chat or starts a new conversation
3. New session defaults to Normal mode (lost RAG mode)
4. User has to manually switch back to RAG mode every time

## Root Cause
Two issues:
1. **Backend** (`desktop_app.py`): `/api/sessions/new` endpoint always saved `mode: "normal"` regardless of what the frontend sent
2. **Frontend** (`desktop_ui/index.html`): `newSession()` function didn't send the current `mode` variable when creating the session

## Fix Applied

### 1. Backend - `desktop_app.py` (lines 293-305)
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

### 2. Frontend - `desktop_ui/index.html` (line 392)
```javascript
async function newSession(){
  const r = await fetch(API+'/api/sessions/new',{method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({mode})}); const d = await r.json();
  sessionId = d.id; const m=document.getElementById('messages'); if(m) m.innerHTML='';
  await loadSessionList();
}
```

### 3. Session loading - `_load_session()` (lines 57-68)
Added defaults for `pinned` and `mode` to handle legacy sessions:
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

## Verification
Tested with curl:
```bash
# Create new session with RAG mode
curl -X POST http://localhost:8732/api/sessions/new -H "Content-Type: application/json" -d '{"mode": "rag"}'
# Response: {"id":"chat_a7c8b3cc64"}

# Verify session file has mode: rag
cat "C:/Users/valte/AppData/Roaming/aether/sessions/chat_a7c8b3cc64.json"
# {"id": "chat_a7c8b3cc64", "title": "(new chat)", "messages": [], "mode": "rag"}

# Verify session endpoint returns mode
curl http://localhost:8732/api/sessions/chat_a7c8b3cc64
# {"id":"chat_a7c8b3cc64","title":"What is RAG?","messages":[...],"mode":"rag","pinned":false}
```

## Files Modified
- `C:/Users/valte/aether/desktop_app.py` - Backend session creation + loading
- `C:/Users/valte/aether/desktop_ui/index.html` - Frontend newSession() call

## Rebuild Required
Since this is a PyInstaller frozen app, the changes require rebuilding:
```bash
cd C:/Users/valte/aether
python build_aether.py
python make_installer.py
```
Then reinstall via the new installer or copy `dist_build/Aether/*` to `C:/Users/valte/AppData/Local/Aether/`.

## Related
- `references/pywebview_desktop_app.md` - Desktop app architecture
- `references/aether_v1.3.0_sessions.md` - Session panel redesign