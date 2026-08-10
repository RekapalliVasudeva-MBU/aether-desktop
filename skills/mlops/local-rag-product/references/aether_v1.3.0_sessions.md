# Aether v1.3.0 — Sessions Panel Redesign

User demand: "the sessions panel only shows delete, not what the chat is — let me find
the session I need, customize names, pin important ones, and see context usage."

## Backend (desktop_app.py)

### `_list_sessions()` — return rich payload
```python
def _list_sessions() -> List[Dict]:
    out = []
    for p in sorted(SESSIONS_DIR.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        msgs = d.get("messages", [])
        preview = ""
        for m in msgs:
            if m.get("role") == "user":
                preview = m["content"][:80]
                break
        total_chars = sum(len(m.get("content", "")) for m in msgs)
        out.append({
            "id": d.get("id", p.stem),
            "title": d.get("title", "(untitled)"),
            "preview": preview,
            "pinned": bool(d.get("pinned", False)),
            "chars": total_chars,
            "files": d.get("files", []),
        })
    def _mtime(s):
        try:
            return (SESSIONS_DIR / f"{s['id']}.json").stat().st_mtime
        except Exception:
            return 0
    # pinned first, then most-recently modified
    out.sort(key=lambda s: (not s["pinned"], -_mtime(s)))
    return out
```
NOTE the sort-key bug: `-SESSIONS_DIR / f"{s['id']}.json".stat().st_mtime` unary-minuses
the Path (TypeError). Compute mtime in a helper and negate THAT.

### `PATCH /api/sessions/{sid}` — rename + pin
```python
@app.patch("/api/sessions/{sid}")
async def api_session_patch(sid: str, req: Request):
    body = await req.json()
    sess = _load_session(sid)
    if "title" in body:
        sess["title"] = body["title"].strip()[:80] or "(untitled)"
    if "pinned" in body:
        sess["pinned"] = bool(body["pinned"])
    _save_session(sid, sess)
    return JSONResponse({"ok": True, "session": {"id": sid, "title": sess["title"], "pinned": sess["pinned"]}})
```

### `POST /api/sessions/{sid}/files` — attach a document
```python
@app.post("/api/sessions/{sid}/files")
async def api_session_add_file(sid: str, req: Request):
    body = await req.json()
    path = body.get("path", "")
    from pathlib import Path as _P
    p = _P(path)
    if not p.exists():
        return JSONResponse({"ok": False, "error": "file not found"})
    sess = _load_session(sid)
    files = sess.get("files", [])
    if path not in files:
        files.append(path)
    sess["files"] = files
    _save_session(sid, sess)
    return JSONResponse({"ok": True, "files": files})
```

### Inject attached files into `api_chat` (BOTH Normal + RAG)
```python
file_context = ""
for fp in sess.get("files", []):
    pp = Path(fp)
    if pp.exists():
        try:
            txt = pp.read_text(encoding="utf-8", errors="ignore")
            file_context += f"\n\n--- Attached document: {pp.name} ---\n{txt[:8000]}\n"
        except Exception:
            pass
# inside event_stream():
system_content = agent.build_system_prompt(mode=mode, rag_context=rag_context)
if file_context:
    system_content += "\n\n# Attached documents for this session (answer using these too):" + file_context
buf = [{"role": "system", "content": system_content}]
```
Verified: model answered "the sky is violet" from an attached `.txt` (Normal mode).

## Frontend (index.html)

### Session row + 3-dot menu
```html
<div class="session-item ${s.id===sessionId?'active':''}" onclick="selectSession('${s.id}');">
  <div class="s-main" onclick="selectSession('${s.id}');">
    <div class="s-title">${pin} ${esc(s.title||s.id)}</div>
    <div class="s-preview">${esc(s.preview||'')}</div>
  </div>
  <div class="s-meta">
    <div class="ctx-circle" title="${pct}% of context used — ${left}% left"
         style="background:conic-gradient(var(--accent) ${pct*3.6}deg, var(--panel2) 0)">
      <span>${pct}%</span>
    </div>
    <button class="dotbtn" onclick="event.stopPropagation();toggleMenu('${s.id}', this)">⋯</button>
    <div class="s-menu" id="menu-${s.id}" style="display:none">
      <button onclick="event.stopPropagation();pinSession('${s.id}', ${s.pinned?0:1})">${s.pinned?'📌 Unpin':'📌 Pin'}</button>
      <button onclick="event.stopPropagation();renameSession('${s.id}')">✏️ Rename</button>
      <button class="danger" onclick="event.stopPropagation();delSession('${s.id}')">🗑 Delete</button>
    </div>
  </div>
</div>
```
`pct = Math.min(100, Math.round((s.chars||0)/120000*100))` (120000 = `MAX_PROMPT_CHARS`).
`selectSession()` MUST call `showView('chat')` first (else `#messages` is null → silent no-op).

### Menu / pin / rename handlers
```js
function toggleMenu(id, el){
  document.querySelectorAll('.s-menu').forEach(m=>{ if(m.id!=='menu-'+id) m.style.display='none'; });
  const m = document.getElementById('menu-'+id);
  m.style.display = (m.style.display==='none'||!m.style.display) ? 'block' : 'none';
}
async function pinSession(id, pinned){
  await fetch(API+'/api/sessions/'+id, {method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify({pinned})});
  await loadSessionList();
}
async function renameSession(id){
  const cur = document.querySelector('.session-item.active .s-title');
  const name = prompt('Rename chat:', cur?cur.textContent.replace('📌','').trim():'');
  if(name===null) return;
  await fetch(API+'/api/sessions/'+id, {method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify({title:name})});
  await loadSessionList();
}
```

### Add-file button (composer) — both modes
```html
<input type="file" id="filepick" style="display:none" onchange="addFileToSession(this)" />
<button class="attach-btn" onclick="document.getElementById('filepick').click()">📎</button>
```
```js
async function addFileToSession(input){
  const f = input.files[0]; if(!f) return;
  if(!sessionId) await newSession();
  await fetch(API+'/api/sessions/'+sessionId+'/files',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:f.path})});
  await renderAttached();
}
```
NOTE: `f.path` in the file input gives the real OS path (works on Windows). To test the
endpoint from bash, don't pass Windows backslash paths through `curl -d` (shell escaping
mangles them) — use `urllib.request` with `json.dumps({'path': r'C:\...'})` or
`--data @file.json`.

### CSS (key bits)
```css
.ctx-circle { width:26px; height:26px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:9px; font-weight:700; }
.ctx-circle span { background:var(--panel); border-radius:50%; width:19px; height:19px; display:flex; align-items:center; justify-content:center; }
.s-menu { position:absolute; right:0; top:26px; background:var(--panel); border:1px solid var(--border); border-radius:9px; z-index:30; display:flex; flex-direction:column; min-width:118px; }
.s-menu button.danger { color:#ff6b6b; }
```

## Verification checklist (live on frozen exe, AETHER_HEADLESS=1)
- [ ] `/api/sessions` returns `title` + `preview` + `pinned` + `chars` + `files`
- [ ] `PATCH pinned:true` → item moves to TOP of list
- [ ] `PATCH title` → persists
- [ ] `POST .../files` with a real path → `ok:true`; bad path → `ok:false`
- [ ] chat with an attached file → model answers from the file's content
- [ ] context circle renders `%` from `chars/120000`
