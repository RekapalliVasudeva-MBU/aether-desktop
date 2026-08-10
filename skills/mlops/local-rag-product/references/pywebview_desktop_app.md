# pywebview desktop app (project_rag_hybrid) — proven skeleton

Real native window, no Chromium download (Windows uses built-in Edge WebView2).
Dep: `pip install pywebview` (pulls bottle + pythonnet).

## Layout (inside project_rag_hybrid/)
- `desktop/desktop_app.py` — adds `desktop/` to `sys.path`, mounts UI routes into bottle,
  starts `api_server.run()` in a daemon thread, then `webview.create_window(...)` +
  `webview.start()` on the MAIN thread.
- `desktop/api_server.py` — bottle routes on 127.0.0.1 only:
  - `GET /api/settings` -> `{provider, model, apikey}` (local UI; safe to send full key,
    Settings tab masks to last 4: `••••xxxx`).
  - `POST /api/settings` -> save provider/model/key to `rag_settings.json`.
  - `POST /api/chat` -> SSE stream (see SSE notes below).
  - `GET /api/files`, `POST /api/upload`, `DELETE /api/delete`, `POST /api/reindex`
    (maps to `rag_pdfs/`).
- `desktop/ui/index.html` — 3 tabs: 💬 Chat (SSE fetch), 📚 Shelf (drag/drop + reindex),
  ⚙️ Settings (provider select, masked key, save). Pure CSS orbs/glass, no 3D runtime.
- `install.py` — asks `Install dependencies now? [Y/n]`, optionally makes a venv,
  `pip install -r requirements.txt`, offers to open the app.
- `requirements.txt` — PyMuPDF, docling, torch, transformers, chromadb,
  sentence-transformers, ollama, openai, pywebview.

## SSE in bottle (critical)
```python
@bottle.route("/api/chat", method="POST")
def chat():
    body = bottle.request.json
    def gen():
        try:
            ... # build ctx, call ollama.chat(stream=True), accumulate frames
            yield f"data: {json.dumps({'token': ''.join(frames)})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    bottle.response.content_type = "text/event-stream"
    bottle.response.headers["Cache-Control"] = "no-cache"
    bottle.response.headers["Access-Control-Allow-Origin"] = "*"
    return gen()   # do NOT wrap in HTTPResponse, do NOT add Connection header
```
- `_get_collection(force=)`: load existing `rag_vector_db` if non-empty (fast), else build
  via `rag.process_rag_pipeline`. Re-index calls with `force=True`.
- UI mounting: register `/ui/<filepath:path>` + `/ui/` before `bottle.run`.

## Pitfalls
- `webview.start()` MUST be on main thread (else "pywebview must be run on a main thread").
- `from api_server import run` fails unless `desktop/` is on `sys.path`.
- pywebview import has no `__version__` attr on 6.2.1 — don't rely on it.

## Logo (WhatsApp-style mark in window + taskbar + installer)
Create ONE mark in 3 forms under `desktop/ui/`:
- `logo.svg` — source of truth.
- `logo.png` (~256px) — top-bar `<img>` + `<link rel="icon">` favicon.
- `logo.ico` — multi-size (16→256) for the EXE/taskbar/shortcut icon.
Generate PNG + ICO with Pillow (no cairosvg needed):
```python
from PIL import Image, ImageDraw
img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
# draw gradient rounded-rect + white mark here...
img.save("desktop/ui/logo.png")
img.save("desktop/ui/logo.ico", sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
```
Wiring:
- Top bar: `<img src="/ui/logo.png">` (replaces any placeholder glyph).
- `<head>`: `<link rel="icon" type="image/png" href="/ui/logo.png">`.
- PyInstaller `sys.argv`: `--icon=desktop/ui/logo.ico` (embeds in exe; log shows
  "Copying icon to EXE"). The `/ui/` bottle static route serves png/ico/svg.
- Inno `.iss`: `SetupIconFile=desktop\\ui\\logo.ico` + `UninstallDisplayIcon={app}\\{#MyAppExe}`.
- **WINDOW/TASKBAR ICON (`icon=`):** modern pywebview (>=4.0) ACCEPTS
  `webview.create_window(..., icon=str(UI_DIR/"logo.ico"))` and applies the mark to
  the native window + taskbar. The old pre-4.0 "TypeError: unexpected keyword
  'icon'" warning NO LONGER HOLDS — set it at runtime, not just build time. If you
  are pinned to a very old pywebview and it rejects `icon=`, fall back to build-time
  `--icon` only. Always serve the `.png` at `/ui/logo.png` so the in-page `<img>` shows.
After install, the desktop shortcut + taskbar show the mark exactly like WhatsApp.

## Hermes-style desktop SIDEBAR (the full feature set the user expects)
The user benchmarks the desktop app against the Hermes desktop they use daily and
expects: a logo, a left sidebar with (a) chat sessions, (b) a **RAG PDFs** panel
(list / add / remove / rebuild index), (c) a **Provider** settings panel (paste
their own API key + model), (d) a **Capabilities** section (toggle Skills / Tools /
MCP / Memory / RAG on-off like Hermes), and (e) a **Gateway** start/stop (Telegram
here — the single messaging integration; if no token, show "not configured").
Layout that worked (FastAPI + pywebview, Aether app):
- `left sidebar (HTML)` sections: Chats / RAG PDFs (count badge) / Provider / Capabilities / Gateway.
- Backend routes to add:
  - `GET /api/capabilities`, `POST /api/capabilities {name,enabled}` -> `config.set_capability()` (persists to config.yaml).
  - `GET /api/config`, `POST /api/settings {api_key, model}` -> `config.set_api_key()` writes the user's OWN `<AETHER_HOME>/.env`; never a sibling app's file (see API-key-leak pitfall in aether_agent_app.md).
  - `GET /api/pdfs`, `POST /api/pdfs/add {path}`, `POST /api/pdfs/remove {path}`, `POST /api/pdfs/rebuild` -> a `pdf_store.py` that ingests a PDF with docling (`DocumentConverter().convert()`), chunks via markdown paragraphs, `collection.add(ids, documents, metadatas=[{source, headings}])`; remove does `collection.delete(where={"source": path})`; rebuild deletes-all then re-adds every tracked source.
  - `GET /api/gateway`, `POST /api/gateway {action:start|stop}` -> a small `gateway_ctl.py` running the Telegram bot in a daemon thread; returns `{configured, running}` (configured = token present).
- Capability toggles must be HONORED inside `run_agent`, not just shown in the UI:
  ```python
  caps = config.get_capabilities()
  if not caps.get("tools", True): schemas = []
  if not caps.get("mcps", True): schemas = [s for s in schemas if not s["name"].startswith("mcp__")]
  rel = skills.find_relevant(q) if caps.get("skills", True) else []
  if "REMEMBER:" in content and caps.get("memory", True): memory.add(fact)
  ```
- RAG mode toggle: UI sets `mode: "rag"` in the `/api/chat` body; backend calls
  `rag.retrieve(q)` and injects it into the system prompt. If `capabilities.rag` is off, skip retrieval.

### PITFALL — desktop chat route must call the REAL agent loop (not provider.chat directly)
The most common reason "the app's agent can't use tools" is that the desktop
`/api/chat` route calls `provider.chat(messages, stream=True)` DIRECTLY, bypassing
`run_agent()` — so tools/skills/MCP never fire inside the app even though the CLI
works. FIX: route the SSE endpoint through the SAME `agent.run_agent(message,
mode=..., rag_context=..., on_token=cb)` loop the CLI uses, then stream the
assembled answer word-by-word. Verified this session: after fixing, the app's
`/api/chat` built `cal_project/calculator.py` using terminal + write_file — exactly
like the CLI. (See aether_agent_app.md for the loop + test.)

### config key-name gotcha
`desktop_app.py` read `cfg["model"]["default_model"]` but the config dict uses the
key `"default"` (`"model": {"provider":..., "default": "openrouter/free", ...}`).
Module-level `grep` for `default_model` would have caught it — but the KeyError only
surfaced at runtime on `/api/config`. Always confirm config key names against
`DEFAULT_CONFIG` before referencing them in route handlers.

## Session management (Hermes-style per-conversation history)
Add `desktop/sessions.py` — DB-style JSON store, one file per session in
`%LOCALAPPDATA%/AetherMindHybrid/sessions/`:
`{id, title, created_at, updated_at, messages:[{role:"user"|"ai", text}]}`.
Dependency-free; mirror of how Hermes keeps per-session history (one file each).
Expose in `desktop/api_server.py`:
- `GET /api/sessions` -> `{sessions:[{id,title,count,...}]}` (newest first)
- `POST /api/sessions/new` -> creates + sets current
- `GET /api/sessions/<sid>` -> loads + sets current
- `DELETE /api/sessions/<sid>`
- `GET /api/sessions/current` -> returns active session or creates one
Hold active id in a module global `_CURRENT = {"sid": None}`.
Persist in the chat `gen()`:
- BEFORE retrieval: `store.append(sid, "user", q)` (auto-title from first user msg)
- AFTER streaming: `store.append(sid, "ai", "".join(frames))`
UI (`desktop/ui/index.html`): left sidebar toggled by ☰ with "+ New chat", clickable
session rows (title + msg count), and a ✕ delete per row. `send()` sends
`session_id: curSid`; on init `fetch('/api/sessions/current')` restores the last
conversation. Render titles via `textContent` (not innerHTML) to satisfy the
innerHTML-XSS lint (localhost-only single-user app).
Verified in the frozen exe: chat persisted both turns (2 msgs after Q1, 4 after Q2)
and reloaded on relaunch.
