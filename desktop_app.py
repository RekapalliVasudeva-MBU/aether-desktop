"""Aether desktop app backend (FastAPI) + native pywebview window.

Two chat modes selectable in the UI:
  - Normal : general agent (tools + skills + memory + MCP)
  - RAG    : grounded on the user's PDF knowledge base

Left sidebar (Hermes-desktop style) exposes:
  - Chats       : new / switch conversations
  - RAG PDFs    : the drop-in folder path, list / add / remove / rebuild
  - Skills      : list every skill, toggle on/off, open & edit, delete
  - Tools       : list every built-in tool, toggle on/off
  - MCP         : list configured servers, toggle, add/remove
  - Memory      : view / edit / delete durable facts
  - Persona     : edit SOUL.md (agent) and USER.md (you)
  - Providers   : pick OpenRouter / OpenAI / Ollama + your own key + model
  - Telegram    : paste a bot token + mode, start/stop the gateway

The backend exposes the REST API the UI calls. The UI lives in desktop_ui/.

Run:  python desktop_app.py
"""
from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from aether import config, agent, rag, skills, memory, pdf_store, gateway_ctl
from aether import mcp as mcp_mod
from aether import tools as tools_mod

ROOT = Path(__file__).resolve().parent
UI_DIR = ROOT / "desktop_ui"
AETHER_HOME = config.AETHER_HOME

app = FastAPI(title="Aether Desktop")

SESSIONS_DIR = AETHER_HOME / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _session_file(sid: str) -> Path:
    return SESSIONS_DIR / f"{sid}.json"


# ---- session store (local JSON per session, Hermes-style) ----
def _load_session(sid: str) -> Dict:
    p = _session_file(sid)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"id": sid, "title": "(new chat)", "messages": []}


def _save_session(sid: str, data: Dict) -> None:
    _session_file(sid).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _list_sessions() -> List[Dict]:
    out = []
    for p in sorted(SESSIONS_DIR.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        out.append({"id": d.get("id", p.stem), "title": d.get("title", "(untitled)")})
    return out


# ---- chat (SSE streaming) ----
@app.post("/api/chat")
async def api_chat(req: Request):
    body = await req.json()
    mode = body.get("mode", "normal")
    message = body.get("message", "")
    sid = body.get("session_id") or f"chat_{int(time.time())}"
    rag_context = ""
    citations = []
    if mode == "rag":
        try:
            rag_context, citations = rag.retrieve_with_citations(message)
        except Exception as e:
            rag_context = f"[RAG retrieval error: {e}]"

    sess = _load_session(sid)
    sess["messages"].append({"role": "user", "content": message})

    reasoning = config.get_reasoning_level()

    def event_stream():
        from aether import provider
        from aether import compression
        buf = [{"role": "system", "content": agent.build_system_prompt(mode=mode, rag_context=rag_context)}]
        for m in sess["messages"]:
            buf.append({"role": m["role"], "content": m["content"]})
        # Hermes-style token saving: trim history before sending to the model
        buf = compression.trim_history(buf)
        try:
            resp = provider.chat(buf, model=body.get("model"), stream=False,
                                 tools=_enabled_schemas(), reasoning_effort=reasoning)
            msg = resp.choices[0].message
            content = msg.content or ""
            tool_calls = getattr(msg, "tool_calls", None)
            if not tool_calls:
                yield f"data: {json.dumps({'token': content, 'session_id': sid, 'citations': citations})}\n\n"
                sess["messages"].append({"role": "assistant", "content": content})
                if not sess.get("title") or sess["title"] == "(new chat)":
                    sess["title"] = message[:40]
                _save_session(sid, sess)
            else:
                # run the tool-calling loop
                full = content
                loop_msgs = list(buf) + [{
                    "role": "assistant", "content": content,
                    "tool_calls": [{"id": tc.id, "type": "function",
                                    "function": {"name": tc.function.name,
                                                 "arguments": tc.function.arguments}}
                                   for tc in tool_calls],
                }]
                turn = 0
                while turn < 12:
                    turn += 1
                    r2 = provider.chat(compression.trim_history(loop_msgs), stream=False,
                                       tools=_enabled_schemas(), reasoning_effort=reasoning)
                    m2 = r2.choices[0].message
                    full += (m2.content or "")
                    if not getattr(m2, "tool_calls", None):
                        break
                    loop_msgs.append({
                        "role": "assistant", "content": m2.content or "",
                        "tool_calls": [{"id": tc.id, "type": "function",
                                        "function": {"name": tc.function.name,
                                                     "arguments": tc.function.arguments}}
                                       for tc in m2.tool_calls],
                    })
                    for tc in m2.tool_calls:
                        fn = tc.function
                        try:
                            args = json.loads(fn.arguments or "{}")
                        except Exception:
                            args = {}
                        result = tools_mod.call_tool(fn.name, args)
                        loop_msgs.append({"role": "tool", "tool_call_id": tc.id, "content": result})
                yield f"data: {json.dumps({'token': full, 'session_id': sid, 'citations': citations})}\n\n"
                sess["messages"].append({"role": "assistant", "content": full})
                if not sess.get("title") or sess["title"] == "(new chat)":
                    sess["title"] = message[:40]
                _save_session(sid, sess)
        except Exception as e:
            yield f"data: {json.dumps({'token': f'[error] {e}', 'session_id': sid})}\n\n"
        yield f"data: {json.dumps({'done': True, 'session_id': sid})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _enabled_schemas() -> List[Dict]:
    """Tool schemas filtered through capability + per-item enable maps."""
    caps = config.get_capabilities()
    specs = agent._tool_specs()
    enabled = {s["name"]: s["enabled"] for s in specs}
    schemas = agent.get_external_tool_schemas()
    if not caps.get("tools", True):
        schemas = []
    else:
        schemas = [s for s in schemas if enabled.get(s["name"], True)]
    if not caps.get("mcps", True):
        schemas = [s for s in schemas if not s["name"].startswith("mcp__")]
    return schemas


# ---- sessions ----
@app.get("/api/sessions")
async def api_sessions():
    return JSONResponse(_list_sessions())


@app.post("/api/sessions/new")
async def api_session_new(req: Request = None):
    import uuid
    sid = f"chat_{uuid.uuid4().hex[:10]}"
    _save_session(sid, {"id": sid, "title": "(new chat)", "messages": []})
    return JSONResponse({"id": sid})


@app.get("/api/sessions/{sid}")
async def api_session_get(sid: str):
    return JSONResponse(_load_session(sid))


# ---- config / settings ----
@app.get("/api/config")
async def api_config():
    cfg = config.load_config()
    return JSONResponse({
        "model": cfg["model"]["default"],
        "provider": cfg["model"]["provider"],
        "has_key": bool(config.get_api_key()),
        "base_url": cfg["model"]["base_url"],
        "reasoning_level": cfg["model"].get("reasoning_level", "auto"),
    })


@app.post("/api/settings")
async def api_settings(req: Request):
    body = await req.json()
    key = (body.get("api_key") or "").strip()
    model = (body.get("model") or "").strip()
    if key:
        config.set_api_key(key)
    if model:
        cfg = config.load_config()
        cfg["model"]["default"] = model
        config.save_config(cfg)
    return JSONResponse({"ok": True, "has_key": bool(config.get_api_key())})


# ---- capabilities (category-level) ----
@app.get("/api/capabilities")
async def api_caps():
    return JSONResponse({"capabilities": config.get_capabilities()})


@app.post("/api/capabilities")
async def api_caps_post(req: Request):
    body = await req.json()
    name = body.get("name", "")
    enabled = bool(body.get("enabled", False))
    if name not in config.get_capabilities():
        return JSONResponse({"ok": False, "error": "unknown capability"})
    new = config.set_capability(name, enabled)
    return JSONResponse({"ok": True, "name": name, "enabled": new})


# ---- per-item toggles ----
@app.post("/api/items/toggle")
async def api_item_toggle(req: Request):
    body = await req.json()
    kind = body.get("kind", "")
    name = body.get("name", "")
    enabled = bool(body.get("enabled", False))
    if kind not in ("skills", "tools", "mcp"):
        return JSONResponse({"ok": False, "error": "bad kind"})
    new = config.set_item_enabled(kind, name, enabled)
    return JSONResponse({"ok": True, "kind": kind, "name": name, "enabled": new})


# ---- skills ----
@app.get("/api/skills")
async def api_skills():
    return JSONResponse({"skills": skills.list_skills()})


@app.get("/api/skills/{name:path}")
async def api_skill_get(name: str):
    return JSONResponse({"name": name, "body": skills.get_skill_body(name)})


@app.post("/api/skills/save")
async def api_skill_save(req: Request):
    body = await req.json()
    name = (body.get("name") or "").strip()
    content = body.get("content", "")
    if not name:
        return JSONResponse({"ok": False, "error": "name required"})
    skills.set_skill_body(name, content)
    return JSONResponse({"ok": True, "name": name})


@app.post("/api/skills/delete")
async def api_skill_delete(req: Request):
    body = await req.json()
    name = body.get("name", "")
    ok = skills.delete_skill(name)
    return JSONResponse({"ok": ok, "name": name})


# ---- tools ----
@app.get("/api/tools")
async def api_tools():
    return JSONResponse({"tools": tools_mod.list_tools()})


@app.post("/api/tools/delete")
async def api_tool_delete(req: Request):
    body = await req.json()
    name = body.get("name", "")
    ok = tools_mod.delete_tool(name)
    return JSONResponse({"ok": ok, "name": name})


# ---- mcp ----
@app.get("/api/mcp")
async def api_mcp():
    return JSONResponse({"servers": mcp_mod.list_servers()})


@app.post("/api/mcp/add")
async def api_mcp_add(req: Request):
    body = await req.json()
    name = (body.get("name") or "").strip()
    spec = body.get("spec") or {}
    ok = mcp_mod.add_server(name, spec)
    return JSONResponse({"ok": ok, "name": name})


@app.post("/api/mcp/delete")
async def api_mcp_delete(req: Request):
    body = await req.json()
    name = body.get("name", "")
    ok = mcp_mod.remove_server(name)
    return JSONResponse({"ok": ok, "name": name})


@app.post("/api/mcp/test")
async def api_mcp_test(req: Request):
    """Live connection probe for one server (spawns a real process for stdio)."""
    name = (await req.json()).get("name", "")
    return JSONResponse(mcp_mod.test_connection(name))


# ---- reasoning level (chat option) ----
@app.get("/api/reasoning")
async def api_reasoning_get():
    return JSONResponse({"level": config.get_reasoning_level()})


@app.post("/api/reasoning")
async def api_reasoning_post(req: Request):
    body = await req.json()
    level = config.set_reasoning_level((body.get("level") or "auto"))
    return JSONResponse({"ok": True, "level": level})


# ---- health (used by the native window to know the server is ready) ----
@app.get("/api/health")
async def api_health():
    return JSONResponse({"ok": True, "version": "1.2.4"})


# ---- memory ----
@app.get("/api/memory")
async def api_memory():
    m = memory.Memory()
    return JSONResponse({"entries": m.all()})


@app.post("/api/memory/delete")
async def api_memory_delete(req: Request):
    body = await req.json()
    idx = int(body.get("index", -1))
    m = memory.Memory()
    ok = m.delete(idx)
    return JSONResponse({"ok": ok})


@app.post("/api/memory/update")
async def api_memory_update(req: Request):
    body = await req.json()
    idx = int(body.get("index", -1))
    content = body.get("content", "")
    m = memory.Memory()
    ok = m.update(idx, content)
    return JSONResponse({"ok": ok})


@app.post("/api/memory/add")
async def api_memory_add(req: Request):
    body = await req.json()
    content = (body.get("content") or "").strip()
    if not content:
        return JSONResponse({"ok": False, "error": "empty"})
    memory.Memory().add(content)
    return JSONResponse({"ok": True})


# ---- persona (SOUL / USER) ----
@app.get("/api/persona/{name}")
async def api_persona_get(name: str):
    if name not in ("SOUL.md", "USER.md"):
        return JSONResponse({"error": "bad name"}, status_code=400)
    return JSONResponse({"name": name, "body": config.read_markdown(name)})


@app.post("/api/persona/save")
async def api_persona_save(req: Request):
    body = await req.json()
    name = body.get("name", "")
    content = body.get("content", "")
    if name not in ("SOUL.md", "USER.md"):
        return JSONResponse({"ok": False, "error": "bad name"})
    config.write_markdown(name, content)
    return JSONResponse({"ok": True, "name": name})


# ---- providers ----
@app.get("/api/providers")
async def api_providers():
    return JSONResponse(config.get_providers())


@app.post("/api/providers/active")
async def api_provider_active(req: Request):
    body = await req.json()
    key = body.get("key", "")
    ok = config.set_active_provider(key)
    return JSONResponse({"ok": ok, "active": config.get_providers()["active"]})


# ---- RAG PDFs ----
@app.get("/api/pdfs")
async def api_pdfs():
    return JSONResponse({"pdfs": pdf_store.list_pdfs(),
                         "dir": str(config.pdf_watch_dir())})


@app.post("/api/pdfs/add")
async def api_pdf_add(req: Request):
    body = await req.json()
    return JSONResponse(pdf_store.add_pdf(body.get("path", "")))


@app.post("/api/pdfs/remove")
async def api_pdf_remove(req: Request):
    body = await req.json()
    return JSONResponse(pdf_store.remove_pdf(body.get("path", "")))


@app.post("/api/pdfs/rebuild")
async def api_pdf_rebuild():
    return JSONResponse(pdf_store.rebuild())


@app.post("/api/pdfs/sync-watchdir")
async def api_pdf_sync():
    """Ingest any new PDFs the user dropped into the watch folder."""
    return JSONResponse(config.index_pdf_watch_dir())


@app.post("/api/openfolder")
async def api_openfolder(req: Request):
    """Reveal a path in the OS file explorer (Windows = os.startfile)."""
    body = await req.json()
    path = body.get("path", "")
    try:
        if os.name == "nt":
            os.startfile(path)  # Windows-only; opens Explorer at the path
        else:
            import subprocess
            subprocess.run(["xdg-open", path], check=False)  # Linux/Mac, arg list (no shell)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})


# ---- Telegram gateway ----
@app.get("/api/telegram")
async def api_tg():
    cfg = config.load_config()["telegram"]
    return JSONResponse({
        "configured": gateway_ctl.is_configured(),
        "running": gateway_ctl.is_running(),
        "token_set": bool(cfg.get("token")),
        "mode": cfg.get("mode", "normal"),
    })


@app.post("/api/telegram/token")
async def api_tg_token(req: Request):
    body = await req.json()
    token = (body.get("token") or "").strip()
    config.set_telegram_token(token)
    return JSONResponse({"ok": True, "configured": bool(token)})


@app.post("/api/telegram/mode")
async def api_tg_mode(req: Request):
    body = await req.json()
    config.set_telegram_mode(body.get("mode", "normal"))
    return JSONResponse({"ok": True})


@app.post("/api/telegram")
async def api_tg_post(req: Request):
    body = await req.json()
    action = body.get("action", "")
    if action == "start":
        return JSONResponse(gateway_ctl.start())
    if action == "stop":
        return JSONResponse(gateway_ctl.stop())
    return JSONResponse({"ok": False, "msg": "unknown action"})


@app.get("/ui/logo.png")
async def logo_png():
    return FileResponse(str(UI_DIR / "logo.png"))


if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(UI_DIR), html=True), name="ui")


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _fail_box(message: str):
    """Show a blocking error dialog (best-effort) and log to a file."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, "Aether", 0x10)
    except Exception:
        pass
    try:
        from pathlib import Path as _P
        import sys as _sys
        log = _P(getattr(_sys, "executable", ".")).parent / "aether_launch.log"
        with open(log, "a", encoding="utf-8") as _lf:
            _lf.write(f"[launch] {message}\n")
    except Exception:
        pass


def main():
    import ctypes
    import threading as _threading
    config.ensure_persona_files()
    # Copy logo.ico next to the exe (the shortcut points here for its icon)
    try:
        src = UI_DIR / "logo.ico"
        if src.exists():
            import shutil
            dst = Path(sys.executable).parent / "logo.ico"
            shutil.copyfile(src, dst)
    except Exception:
        pass
    # Ingest any PDFs the user dropped into the watch folder (zero-config RAG).
    # Do this in the BACKGROUND so it can never delay the server from binding
    # (a slow cold-start ingest used to exceed the startup probe and show the
    # "could not start backend" error even though the server was fine).
    def _bg_ingest():
        try:
            res = config.index_pdf_watch_dir()
            if res.get("added"):
                print(f"[rag] auto-ingested {res['added']} PDF(s) "
                      f"({res['chunks']} chunks) from {res['dir']}")
        except Exception as e:
            print(f"[rag] watch-dir ingest skipped: {e}")
    _threading.Thread(target=_bg_ingest, daemon=True).start()

    import ctypes
    import threading as _threading

    # ---- Single instance (Windows named mutex) ----
    # Only ONE Aether.exe may run at a time. This avoids the WebView2
    # "two instances conflict" failure that forced the browser fallback.
    MUTEX_NAME = "Global\\AetherSingleInstanceMutex"
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, 0, MUTEX_NAME)
    last_err = kernel32.GetLastError()
    already_running = (last_err == 183)  # ERROR_ALREADY_EXISTS

    def _focus_existing_window():
        """Bring the running Aether window to the foreground."""
        try:
            user32 = ctypes.windll.user32
            EnumWindows = user32.EnumWindows
            GetWindowTextW = user32.GetWindowTextW
            GetWindowTextLengthW = user32.GetWindowTextLengthW
            IsWindowVisible = user32.IsWindowVisible
            ShowWindow = user32.ShowWindow
            SetForegroundWindow = user32.SetForegroundWindow
            SW_RESTORE = 9

            target_title = "Aether — AI Agent + Personal RAG"

            def cb(hwnd, _):
                if not IsWindowVisible(hwnd):
                    return True
                length = GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True
                buf = ctypes.create_unicode_buffer(length + 1)
                GetWindowTextW(hwnd, buf, length + 1)
                if target_title in buf.value:
                    ShowWindow(hwnd, SW_RESTORE)
                    SetForegroundWindow(hwnd)
                    return False  # stop enumerating
                return True

            EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(cb), 0)
        except Exception:
            pass

    if already_running:
        print("[desktop] another Aether instance is already running — focusing it")
        _focus_existing_window()
        # Exit without spawning a server or opening a browser.
        try:
            kernel32.ReleaseMutex(mutex)
        except Exception:
            pass
        return

    # ---- We are the only instance: serve on the fixed port + native window ----
    import uvicorn
    import urllib.request
    port = int(os.environ.get("AETHER_PORT", "8732"))
    url = f"http://127.0.0.1:{port}/ui/"
    health_url = f"http://127.0.0.1:{port}/api/health"

    def _port_taken() -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(("127.0.0.1", port)) == 0

    # If the port is genuinely taken by something other than our own server
    # (e.g. a stale non-Aether process), surface it instead of ERR_CONNECTION_REFUSED.
    if _port_taken():
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Aether can't start: port {port} is already in use by another "
                f"program.\n\nClose that program (or set AETHER_PORT to a free port) "
                f"and relaunch Aether.",
                "Aether", 0x10,
            )
        except Exception:
            pass
        try:
            kernel32.ReleaseMutex(mutex)
        except Exception:
            pass
        return

    def _serve():
        import traceback
        log = Path(os.environ.get("LOCALAPPDATA", "")) / "Aether" / "aether_startup.log"
        try:
            with open(log, "a", encoding="utf-8") as f:
                f.write(f"[server] starting uvicorn on {port}...\n")
            uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
        except Exception:
            try:
                with open(log, "a", encoding="utf-8") as f:
                    f.write("[server] uvicorn.run raised:\n" + traceback.format_exc() + "\n")
            except Exception:
                pass

    _threading.Thread(target=_serve, daemon=True).start()

    # PERMANENT fix for ERR_CONNECTION_REFUSED: wait until the server actually
    # answers /api/health before we ever hand the URL to WebView2. No race,
    # no random-port fallback, no browser.
    server_ready = False
    for _ in range(90):  # up to ~45s — generous for cold/first-run startup
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(health_url, timeout=1) as r:
                if r.status == 200:
                    server_ready = True
                    break
        except Exception:
            continue
    if not server_ready:
        _fail_box(
            "Aether could not start its backend server.\n\n"
            "The local API did not become ready in time. This usually means "
            f"port {port} is already in use, a previous Aether process is "
            "still shutting down, or the first launch is slow on your machine "
            "(RAG indexing). Wait a moment, ensure no other Aether is running, "
            "and relaunch.\n\n"
            "If it keeps failing, set AETHER_PORT to a free port and relaunch."
        )
        try:
            kernel32.ReleaseMutex(mutex)
        except Exception:
            pass
        return

    # PRIMARY + ONLY: native pywebview window (WebView2 is installed).
    # In AETHER_HEADLESS mode (testing/CI) we skip the window and just keep
    # the server alive so it can be probed from the outside.
    if os.environ.get("AETHER_HEADLESS") == "1":
        print("[desktop] headless mode — server only, no window")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
        try:
            kernel32.ReleaseMutex(mutex)
        except Exception:
            pass
        return

    started_native = False
    try:
        import webview
        # NOTE: create_window() in this pywebview version has no `icon` kwarg.
        # The window/taskbar icon is set via PyInstaller --icon at build time.
        w = webview.create_window(
            "Aether — AI Agent + Personal RAG",
            url=url,
            width=1280, height=840,
            text_select=True,
            confirm_close=False,
        )
        _hwnd = getattr(w, "hWnd", None)

        def _restore():
            if _hwnd:
                try:
                    ctypes.windll.user32.ShowWindow(_hwnd, 9)  # SW_RESTORE
                    ctypes.windll.user32.SetForegroundWindow(_hwnd)
                except Exception:
                    pass

        webview.start(func=_restore, gui=None,
                      icon=str(Path(sys.executable).parent / "logo.ico"))
        started_native = True
    except Exception as e:
        import traceback as _tb
        print(f"[desktop] native window failed: {e}")
        try:
            with open(Path(sys.executable).parent / "aether_launch.log", "a") as _lf:
                _lf.write(f"[launch] webview failed: {e}\n{_tb.format_exc()}\n")
        except Exception:
            pass
        _fail_box(
            f"Aether could not start its native window:\n{e}\n\n"
            "WebView2 may be missing or blocked. Install the WebView2 Runtime "
            "from Microsoft, then relaunch Aether."
        )

    # Keep the process alive while the window is open (webview.start blocks,
    # but guard anyway so the server thread stays up if webview returned early).
    if started_native:
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
    else:
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
    try:
        kernel32.ReleaseMutex(mutex)
    except Exception:
        pass


if __name__ == "__main__":
    main()
