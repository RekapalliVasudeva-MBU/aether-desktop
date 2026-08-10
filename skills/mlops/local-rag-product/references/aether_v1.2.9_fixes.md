# Aether v1.2.9 — three bugs fixed (recurring-class patterns)

These three failures are NOT one-offs; they will recur on the next UI/mutex/ingest
change. Embed the lesson, don't re-debug from scratch.

## 1. Sessions panel: clicking a past chat did nothing (only 🗑 delete worked)

**Symptom the user reports:** "when I click on previous chat it only shows the option
to delete it, not [the chat]". Reads as "the app can't do basic tasks".

**Root cause:** `selectSession(id)` rendered messages into the `#messages` element.
But `#messages` only exists while the **Chat view** is rendered (`renderChat()` sets
`view.innerHTML`). The Sessions panel lives in the **sidebar** (always visible). If the
user was on any other view (RAG PDFs, Settings, …) when they clicked a session,
`document.getElementById('messages')` returned **null** → `if(!m) return;` → silent no-op.
The delete button is in the sidebar so it always worked, masking the bug.

**Fix:** `selectSession` must switch to the Chat view FIRST, before touching `#messages`:
```js
async function selectSession(id){
  showView('chat');                       // ensures #messages exists
  sessionId = id;
  const r = await fetch(API+'/api/sessions/'+id); const d = await r.json();
  const m = document.getElementById('messages'); if(!m) return; m.innerHTML='';
  (d.messages||[]).forEach(x => addMsg(x.role, x.content));
  await loadSessionList();
}
```
Also the Sessions header `＋` (new chat) button must `showView('chat')` before
`newSession()`.

**Verification trap:** backend `/api/sessions/{id}` returning messages is NOT proof the
UI works — the bug was 100% client-side (null element). Drive a REAL headless launch +
simulate the click path / inspect the rendered DOM, or just confirm `showView('chat')`
is the first line of `selectSession`.

## 2. App wouldn't open (single-instance mutex)

**Symptom:** double-clicking the shortcut did nothing / no window. Log said
`[desktop] another Aether instance is already running — focusing it` on every launch.

**Two root causes:**
(a) A crashed/stale `Aether.exe` (often the 2GB zombie stuck mid-docling-ingest) holds
the named mutex `Global\AetherSingleInstanceMutex` and the port is dead. Every new launch
saw `GetLastError()==183` (ERROR_ALREADY_EXISTS) and bailed — focusing a window that
didn't exist. Classic "app won't open" with no error shown to the user.
(b) A ctypes mistake I introduced: `_CreateMutexW.errcheck = None` — ctypes requires
`errcheck` to be callable or omitted; `None` raises `TypeError: the errcheck attribute
must be callable` and the new build crashed at startup (before uvicorn bound).

**Fix (mutex liveness check):**
```python
import ctypes
kernel32 = ctypes.windll.kernel32
_CreateMutexW = kernel32.CreateMutexW
_CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
_CreateMutexW.restype = ctypes.c_void_p
# NOTE: do NOT set .errcheck = None — it must be callable or absent
mutex = _CreateMutexW(None, 0, MUTEX_NAME)
last_err = ctypes.GetLastError()
already_running = (last_err == 183)

def _other_instance_alive() -> bool:
    import urllib.request
    port = int(os.environ.get("AETHER_PORT", "8732"))
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False

# Stale mutex from a dead instance → take over instead of bailing.
if already_running and not _other_instance_alive():
    print("[desktop] stale mutex from a dead instance — taking over")
    try: kernel32.ReleaseMutex(mutex)
    except Exception: pass
    already_running = False
```
If `already_running` is still True after this (a real live instance exists), the existing
`_focus_existing_window()` path runs.

**Gotcha:** a frozen exe's `GetLastError()` via `ctypes.windll` is unreliable unless you
declare `argtypes`/`restype` on the prototype (done above). The old code called
`kernel32.CreateMutexW(...)` then `kernel32.GetLastError()` with no prototype — flaky.

## 3. RAG chat couldn't answer from the user's PDFs (empty ChromaDB)

**Symptom:** "the rag chat is unable to process or answer it" even though PDFs were copied
into `C:\Users\valte\AppData\Roaming\aether\rag_pdfs`.

**Root cause:** the ChromaDB collection (`docling_knowledge_base`) was **EMPTY** (0 chunks).
The startup daemon calls `config.index_pdf_watch_dir()` which loops `pdf_store.add_pdf`
per PDF — but docling is slow on CPU (~30–60s/PDF, loads OCR models each time) and any
per-PDF exception aborted the whole loop (or the error was swallowed by the daemon thread),
leaving the collection empty. The user pasted 29 files; none were indexed.

**Fixes:**
- Make `index_pdf_watch_dir()` resilient: wrap each `add_pdf` in try/except, collect
  `errors`, and continue — one bad/scanned PDF must not abort the batch:
```python
for p in sorted(wd.glob("*.pdf")):
    if str(p) in indexed: continue
    try:
        r = pdf_store.add_pdf(str(p))
    except Exception as e:
        errors.append(f"{p.name}: {e}"); continue
    if r.get("ok"):
        added += 1; chunks += r.get("chunks", 0)
    else:
        errors.append(f"{p.name}: {r.get('error')}")
return {"ok": True, "added": added, "chunks": chunks, "dir": str(wd), "errors": errors}
```
- Actually run the ingest as a background task (not just rely on silent startup):
  `python -c "from aether import config; print(config.index_pdf_watch_dir())"` →
  verified **25 PDFs / 344 chunks / 0 errors** (the 4 non-PDFs were `.md`/`.png`/
  `temp_split_chunks` subfolder, correctly skipped).
- Verify the collection is non-empty before declaring RAG fixed:
  `from aether import rag; print(rag.get_collection().count())` must be > 0.
- The "Sync folder" UI button (`/api/pdfs/sync-watchdir`) already shows status — make
  sure the backend returns `errors` so the UI can surface a partial failure.

**Why this matches the website:** `project_rag` uses the SAME docling → ChromaDB
`docling_knowledge_base` pipeline. The desktop app's RAG is "same as the website" only
if the desktop ChromaDB is actually populated — the empty-collection state made them
diverge. After ingest, desktop RAG returns the same 📚 source citations.

## Release note
Shipped as v1.2.9 (portable zip, no installer — Inno Setup not installed on build box).
Installed copy at `%LOCALAPPDATA%\Aether` updated by copying `dist_build/Aether/*` over it.
