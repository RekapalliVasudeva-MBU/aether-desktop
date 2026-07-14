"""Aether desktop app backend (FastAPI) + pywebview window.

Two chat modes selectable in the UI:
  - Normal : general agent (tools + skills + memory + MCP)
  - RAG    : grounded on the user's PDF knowledge base

Left sidebar (Hermes-desktop style) exposes:
  - Sessions (new / switch)
  - RAG PDFs panel : list / add / remove / rebuild the knowledge base
  - Provider settings : paste your own OpenRouter API key + model
  - Capabilities : toggle skills / tools / mcps / memory / rag on/off
  - Gateway : start / stop the Telegram integration (if configured)

The backend exposes:
  GET  /ui/            -> desktop UI
  GET  /ui/logo.png    -> app icon
  POST /api/chat       -> {mode, message, session_id, rag_db} -> SSE stream of tokens
  GET  /api/sessions   -> list sessions
  POST /api/sessions/new
  GET  /api/sessions/<id>
  GET  /api/skills
  GET  /api/capabilities
  POST /api/capabilities {name, enabled}
  GET  /api/config      -> {model, has_key, base_url}
  POST /api/settings    -> {api_key, model}
  GET  /api/pdfs        -> list indexed PDFs
  POST /api/pdfs/add    -> {path} ingest a PDF
  POST /api/pdfs/remove -> {path} delete a PDF's chunks
  POST /api/pdfs/rebuild
  GET  /api/gateway     -> {configured, running}
  POST /api/gateway     -> {action: start|stop}

Run:  python desktop_app.py
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from aether import config, agent, rag, skills, memory, pdf_store, gateway_ctl

ROOT = Path(__file__).resolve().parent
UI_DIR = ROOT / "desktop_ui"
AETHER_HOME = config.AETHER_HOME

app = FastAPI(title="Aether Desktop")

# ---- session store (local JSON per session, Hermes-style) ----
SESSIONS_DIR = AETHER_HOME / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _session_file(sid: str) -> Path:
    return SESSIONS_DIR / f"{sid}.json"


def list_sessions() -> List[Dict]:
    out = []
    for f in SESSIONS_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            out.append({"id": d.get("id"), "title": d.get("title", "(untitled)"),
                        "messages": len(d.get("messages", []))})
        except Exception:
            pass
    return out


def new_session() -> str:
    sid = uuid.uuid4().hex[:12]
    _session_file(sid).write_text(
        json.dumps({"id": sid, "title": "New chat", "messages": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    return sid


def append_message(sid: str, role: str, content: str):
    p = _session_file(sid)
    if not p.exists():
        new_session()
    d = json.loads(p.read_text(encoding="utf-8"))
    if d["title"] == "New chat" and role == "user":
        d["title"] = content[:50]
    d.setdefault("messages", []).append({"role": role, "content": content})
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def get_messages(sid: str) -> List[Dict]:
    p = _session_file(sid)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("messages", [])


# ---- chat endpoint (SSE) : routes through the real agent loop (tools + skills) ----
@app.post("/api/chat")
async def chat(req: Request):
    body = await req.json()
    mode = body.get("mode", "normal")
    message = body.get("message", "")
    sid = body.get("session_id") or new_session()

    append_message(sid, "user", message)

    rag_ctx = ""
    if mode == "rag":
        try:
            rag_ctx = rag.retrieve(message)
        except Exception as e:
            rag_ctx = f"[RAG retrieval error: {e}]"

    caps = config.get_capabilities()

    def gen():
        full = []
        try:
            # Always route through the real agent loop (uses tools/skills/mcp
            # when enabled; capability toggles are honored inside run_agent).
            from aether import provider
            answer = agent.run_agent(
                message, mode=mode, rag_context=rag_ctx,
                on_token=lambda t: full.append(t),
            )
            if not full:
                full = [answer]
            # stream the assembled answer as word chunks
            text = "".join(full)
            words = text.split(" ")
            for i, w in enumerate(words):
                tok = w + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'token': tok})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'token': f'[error] {e}'})}\n\n"
        final_text = "".join(full)
        append_message(sid, "assistant", final_text)
        yield f"data: {json.dumps({'done': True, 'session_id': sid})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/sessions")
async def api_sessions():
    return JSONResponse(list_sessions())


@app.post("/api/sessions/new")
async def api_new_session():
    return JSONResponse({"id": new_session()})


@app.get("/api/sessions/{sid}")
async def api_get_session(sid: str):
    return JSONResponse({"id": sid, "messages": get_messages(sid)})


@app.get("/api/current_session")
async def api_current():
    sessions = list_sessions()
    if sessions:
        return JSONResponse({"session_id": sessions[0]["id"]})
    return JSONResponse({"session_id": new_session()})


@app.get("/api/skills")
async def api_skills():
    return JSONResponse({"skills": list(skills.discover().keys())})


@app.get("/api/capabilities")
async def api_caps():
    return JSONResponse({"capabilities": config.get_capabilities()})


@app.post("/api/capabilities")
async def api_set_cap(req: Request):
    body = await req.json()
    name = body.get("name", "")
    enabled = bool(body.get("enabled", False))
    ok = config.set_capability(name, enabled)
    return JSONResponse({"name": name, "enabled": ok})


@app.get("/api/config")
async def api_config():
    cfg = config.load_config()
    return JSONResponse({
        "model": cfg["model"]["default"],
        "base_url": cfg["model"]["base_url"],
        "has_key": bool(config.get_api_key()),
    })


@app.post("/api/settings")
async def api_settings(req: Request):
    body = await req.json()
    if body.get("api_key"):
        config.set_api_key(body["api_key"])
    if body.get("model"):
        cfg = config.load_config()
        cfg["model"]["default"] = body["model"]
        config.save_config(cfg)
    return JSONResponse({"ok": True, "has_key": bool(config.get_api_key()),
                         "model": config.load_config()["model"]["default"]})


# ---- RAG PDF management ----
@app.get("/api/pdfs")
async def api_pdfs():
    return JSONResponse({"pdfs": pdf_store.list_pdfs()})


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


# ---- Gateway (Telegram) control ----
@app.get("/api/gateway")
async def api_gw():
    return JSONResponse({"configured": gateway_ctl.is_configured(),
                         "running": gateway_ctl.is_running()})


@app.post("/api/gateway")
async def api_gw_post(req: Request):
    body = await req.json()
    action = body.get("action", "")
    if action == "start":
        return JSONResponse(gateway_ctl.start())
    if action == "stop":
        return JSONResponse(gateway_ctl.stop())
    return JSONResponse({"ok": False, "msg": "unknown action"})


@app.get("/ui/logo.png")
async def logo():
    return FileResponse(str(UI_DIR / "logo.png"))


if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(UI_DIR), html=True), name="ui")


def main():
    config.ensure_persona_files()
    import uvicorn
    import threading

    port = int(os.environ.get("AETHER_PORT", "8732"))
    url = f"http://127.0.0.1:{port}/ui/"

    def _serve():
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

    t = threading.Thread(target=_serve, daemon=True)
    t.start()

    try:
        import webview
        icon = str(UI_DIR / "logo.ico")
        webview.create_window(
            "Aether — AI Agent + RAG",
            url=url,
            width=1200, height=820,
            icon=icon,        # window + taskbar icon (Hermes-desktop style)
            text_select=True,
        )
        webview.start()
    except Exception as e:
        print(f"[desktop] webview unavailable ({e}); server running at {url}")
        try:
            import time
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
