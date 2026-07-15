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
    if mode == "rag":
        try:
            rag_context = rag.retrieve(message)
        except Exception as e:
            rag_context = f"[RAG retrieval error: {e}]"

    sess = _load_session(sid)
    sess["messages"].append({"role": "user", "content": message})

    def event_stream():
        from aether import provider
        buf = [{"role": "system", "content": agent.build_system_prompt(mode=mode, rag_context=rag_context)}]
        for m in sess["messages"]:
            buf.append({"role": m["role"], "content": m["content"]})
        try:
            resp = provider.chat(buf, model=body.get("model"), stream=False, tools=_enabled_schemas())
            msg = resp.choices[0].message
            content = msg.content or ""
            tool_calls = getattr(msg, "tool_calls", None)
            if not tool_calls:
                yield f"data: {json.dumps({'token': content, 'session_id': sid})}\n\n"
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
                    r2 = provider.chat(loop_msgs, stream=False, tools=_enabled_schemas())
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
                yield f"data: {json.dumps({'token': full, 'session_id': sid})}\n\n"
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


def main():
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
    try:
        res = config.index_pdf_watch_dir()
        if res.get("added"):
            print(f"[rag] auto-ingested {res['added']} PDF(s) "
                  f"({res['chunks']} chunks) from {res['dir']}")
    except Exception as e:
        print(f"[rag] watch-dir ingest skipped: {e}")

    import uvicorn
    port = int(os.environ.get("AETHER_PORT", "8732"))

    # Single instance: if 8732 is already taken by an orphaned process, bind to
    # a free port instead of silently exiting — the user must always see a window.
    if _port_in_use(port):
        import socket as _s
        with _s.socket(_s.AF_INET, _s.SOCK_STREAM) as _ss:
            _ss.bind(("127.0.0.1", 0))
            port = _ss.getsockname()[1]
        print(f"[desktop] port 8732 busy — using {port} instead")

    url = f"http://127.0.0.1:{port}/ui/"

    def _serve():
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

    threading.Thread(target=_serve, daemon=True).start()
    time.sleep(1.5)

    # PRIMARY: native pywebview window (WebView2 is installed on this machine).
    # FALLBACK: open the default browser if the native window can't start.
    started_native = False
    try:
        import webview
        icon = str(Path(sys.executable).parent / "logo.ico")
        webview.create_window(
            "Aether — AI Agent + Personal RAG",
            url=url,
            width=1280, height=840,
            icon=icon,
            text_select=True,
            confirm_close=False,
        )
        webview.start()
        started_native = True
    except Exception as e:
        print(f"[desktop] native window unavailable ({e}) — opening browser")
        webbrowser.open(url)

    if not started_native:
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
