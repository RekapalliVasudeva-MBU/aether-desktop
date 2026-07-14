"""Cloud-ready AetherMind server for free hosting (Render / Hugging Face Spaces).

Self-contained: serves the SAME premium UI + /knowledge page + /api/chat
(RAG over the bundled vector DB) using OpenRouter (no GPU needed). The laptop
does NOT need to be on — deploy this once and the site runs 24/7 for free.

The vector DB (rag_vector_db/, 10MB) and web_ui/ are copied alongside this
file by build_deploy.py before deploying.

Env vars (set in the cloud dashboard):
  OPENROUTER_API_KEY   (required)
  OPENROUTER_MODEL     (optional, default openrouter/free)
  PORT                 (set automatically by the platform)
"""
from __future__ import annotations

import os
import json
import time
import asyncio
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="AetherMind (cloud)")

BASE = Path(__file__).resolve().parent
UI_DIR = BASE / "web_ui"
DB_DIR = BASE / "rag_vector_db"
COLLECTION = os.environ.get("AETHER_COLLECTION", "docling_knowledge_base")


def _api_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY", "")


def get_collection():
    import chromadb
    client = chromadb.PersistentClient(path=str(DB_DIR))
    return client.get_or_create_collection(COLLECTION)


def retrieve(query: str, n: int = 6):
    col = get_collection()
    res = col.query(query_texts=[query], n_results=min(n * 2, 20))
    docs, metas = res["documents"][0], res["metadatas"][0]
    out = ""
    for d, m in zip(docs[:n], metas[:n]):
        out += f"--- {m.get('source','?')} | {m.get('headings','')} ---\n{d}\n\n"
    return out


def build_prompt(context: str, q: str) -> str:
    return (
        "You are an expert AI Engineering Assistant. Answer clearly and directly "
        "based ONLY on the provided context. If the answer is not in the context, "
        "say you don't have enough information.\n\n"
        f"CONTEXT:\n{context}\n\nQUESTION: {q}"
    )


@app.get("/")
async def index():
    p = UI_DIR / "index.html"
    return FileResponse(p) if p.exists() else HTMLResponse("<h1>AetherMind</h1>")


@app.get("/knowledge")
async def knowledge():
    p = UI_DIR / "knowledge.html"
    return FileResponse(p) if p.exists() else HTMLResponse("<h1>Knowledge</h1>")


@app.get("/ui/logo.png")
async def logo():
    return FileResponse(UI_DIR / "logo.png") if (UI_DIR / "logo.png").exists() else HTMLResponse("")


@app.post("/api/chat")
async def chat(req: Request):
    body = await req.json()
    q = body.get("question", "")
    key = _api_key()
    if not key:
        return JSONResponse({"error": "OPENROUTER_API_KEY not set on the server."}, status_code=500)
    context = retrieve(q)
    system = build_prompt(context, q)
    from openai import OpenAI
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key,
                    default_headers={"HTTP-Referer": "https://aethermind", "X-Title": "AetherMind"})

    def gen():
        stream = client.chat.completions.create(
            model=os.environ.get("OPENROUTER_MODEL", "openrouter/free"),
            messages=[{"role": "system", "content": system}, {"role": "user", "content": q}],
            stream=True,
        )
        for chunk in stream:
            tok = ""
            try:
                if chunk.choices and chunk.choices[0].delta:
                    tok = chunk.choices[0].delta.content or ""
            except Exception:
                tok = ""
            if tok:
                yield f"data: {json.dumps({'token': tok})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(UI_DIR), html=True), name="ui")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
