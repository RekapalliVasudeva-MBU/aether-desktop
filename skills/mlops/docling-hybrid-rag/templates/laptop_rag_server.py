"""Laptop-as-server RAG skeleton (FastAPI + SSE + serial queue + hardening).

Copy into a project_rag-style folder. Reads from an existing docling-built
ChromaDB collection and streams answers from the LOCAL Ollama model, one user
at a time. Includes the proven hardening from the live deploy: query cleaning,
answer cache, robust fallback prompt, and a client-side double-submit guard.
Run: python laptop_rag_server.py
"""
import asyncio, json, uuid
from pathlib import Path
from collections import deque
from datetime import datetime

import chromadb
from chromadb.utils import embedding_functions
import ollama
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from contextlib import asynccontextmanager

PROJECT_DIR = Path(__file__).parent
client = chromadb.PersistentClient(path=str(PROJECT_DIR / "rag_vector_db"))
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2")
collection = client.get_collection("docling_knowledge_base", embedding_function=emb_fn)

OLLAMA_MODEL = "richardyoung/qwythos-9b-abliterated:Q4_K_M"

_queue = deque()
_queue_lock = asyncio.Lock()
_current = None

# --- answer cache: keyed on cleaned query, TTL 1h ---
_CACHE: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 3600.0

_STOP = {"can", "u", "you", "say", "tell", "me", "what", "is", "are",
         "do", "does", "the", "a", "an", "of", "to", "in", "on", "for",
         "about", "please", "hi", "hello", "explain"}


def _clean_query(q: str) -> str:
    words = [w for w in q.lower().replace("?", " ").split() if w not in _STOP]
    return " ".join(words) if words else q


def _cache_get(q: str):
    k = _clean_query(q)
    if k in _CACHE:
        ans, ts = _CACHE[k]
        if (datetime.now().timestamp() - ts) < _CACHE_TTL:
            return ans
        del _CACHE[k]
    return None


def _cache_put(q: str, ans: str):
    _CACHE[_clean_query(q)] = (ans, datetime.now().timestamp())


def _build_prompt(ctx: str, had_context: bool) -> str:
    if not had_context:
        return ('You are a retrieval-augmented assistant. No relevant context was '
                'found. Reply EXACTLY with: "I don\'t have information about that in '
                'my knowledge base." Do not use outside knowledge.')
    return ("You are an expert AI assistant. Answer clearly from the CONTEXT. "
            "If the fact is genuinely not in the CONTEXT, say so briefly. "
            "Do not use outside knowledge. Be concise.\n\nCONTEXT:\n" + ctx)


async def generate(question: str, session_id: str):
    loop = asyncio.get_running_loop()

    # 0) cache hit => instant, no GPU
    cached = _cache_get(question)
    if cached is not None:
        yield f"data: {json.dumps({'token': cached})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
        return

    # 1) retrieve offloaded to thread (blocking disk IO); search on CLEANED query
    results = await loop.run_in_executor(None, lambda: collection.query(
        query_texts=[_clean_query(question)], n_results=5))
    ctx = ""
    docs = results["documents"][0] if results["documents"] else []
    for i, doc in enumerate(docs):
        src = results["metadatas"][0][i]["source"]
        head = results["metadatas"][0][i]["headings"]
        ctx += f"--- Chunk {i+1} (Source: {src} | Section: {head}) ---\n{doc}\n\n"
    had_context = len(docs) > 0 and any(d.strip() for d in docs)

    # 2) generate: iterate ollama stream in THIS thread (never asyncio.to_thread!)
    stream = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "system", "content": _build_prompt(ctx, had_context)},
                  {"role": "user", "content": question}],
        options={"keep_alive": "-1"},
        stream=True,
    )
    full = []
    for chunk in stream:
        token = chunk["message"]["content"] if "message" in chunk else ""
        if token:
            full.append(token)
            yield f"data: {json.dumps({'token': token})}\n\n"
    _cache_put(question, "".join(full))
    yield f"data: {json.dumps({'done': True})}\n\n"


async def worker():
    global _current
    while True:
        async with _queue_lock:
            if not _queue:
                await asyncio.sleep(0.2)
                continue
            item = _queue.popleft()
        _current = item["session_id"]
        try:
            async for piece in generate(item["question"], item["session_id"]):
                await item["enqueue"](piece)
        finally:
            _current = None
            await item["enqueue"](None)


@asynccontextmanager
async def lifespan(app):
    asyncio.create_task(worker())
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    q = (body.get("question") or "").strip()
    if not q:
        return JSONResponse({"error": "empty"}, status_code=400)

    async def event_stream():
        qx = asyncio.Queue()
        _queue.append({"question": q, "session_id": str(uuid.uuid4())[:12],
                       "enqueue": qx.put})
        while True:
            piece = await qx.get()
            if piece is None:
                break
            yield piece

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

# ---------------------------------------------------------------------------
# CLIENT GUARD (put this in the chat UI's JS, NOT the server — prevents a
# flaky phone->ngrok retry from opening a 2nd stream into the same box):
#
#   let _busy = false;
#   async function send(){
#     if(_busy) return;                 // ignore double-submits / retries
#     _busy = true;
#     ... open fetch('/api/chat') and stream tokens into the box ...
#     ... on reader done OR catch: _busy = false;  // ALWAYS reset
#   }
# ---------------------------------------------------------------------------
