# OpenRouter conversion + 24/7 cloud deploy (AetherMind)

## Why
The laptop is the server, so the site dies when it's off/reboots, and local
Ollama needs the GPU + model pinned. Two fixes, both verified this session:

1. **Website → OpenRouter** (`project_rag/server.py`): drop local Ollama entirely;
   generate via OpenRouter's OpenAI-compatible endpoint. No GPU, no model-pin,
   portable to any host.
2. **True 24/7 when laptop is OFF**: bundle a self-contained cloud server
   (`deploy/cloud_server.py` + copied `rag_vector_db/` + `web_ui/`) and deploy to
   a FREE host (Render Blueprint / HF Spaces Docker). This is the ONLY way
   "site runs even when my laptop is off" is physically possible.

## OpenRouter server pattern (replaces ollama.chat)
```python
from openai import OpenAI
api_key = (CONFIG.get("openrouter_api_key")
           or os.environ.get("OPENROUTER_API_KEY")
           or _hermes_openrouter_key())   # reuse hermes .env (user authorized)
if not api_key:
    yield f"data: {json.dumps({'error': 'OpenRouter API key not configured.'})\n\n"
    return
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
    default_headers={"HTTP-Referer": "https://localhost/rag", "X-Title": "AetherMind"},
)
om_model = CONFIG.get("openrouter_model", "openrouter/free")
response_stream = client.chat.completions.create(
    model=om_model,
    messages=[{"role": "system", "content": system_prompt},
              {"role": "user", "content": user_question}],
    stream=True,
)
for chunk in response_stream:
    token = ""
    try:
        if chunk.choices and chunk.choices[0].delta:
            token = chunk.choices[0].delta.content or ""
    except Exception:
        token = ""
    if token:
        yield f"data: {json.dumps({'token': token})}\n\n"
yield f"data: {json.dumps({'done': True})}\n\n"
```
Read the key from hermes `.env` (Local or Roaming `hermes/.env`, or `~/.hermes/.env`)
by scanning for `OPENROUTER_API_KEY=`. Add `openrouter_api_key` + `openrouter_model`
to server config defaults (leave empty → auto-read).

## `openrouter/free` free-check quirk
The literal model `openrouter/free` IS free, but a naive
`if not model.endswith(":free"): warn(...)` FALSE-POSITIVES on it (it ends in
`/free`, not `:free`). Correct check:
```python
if ":free" not in model and not model.startswith("openrouter/free"):
    print("[warn] model is not :free; you may be billed.")
```

## Cloud server (self-contained, for Render/HF)
`deploy/cloud_server.py` (FastAPI): serves `web_ui/`, `/knowledge`, `/ui/logo.png`,
and `/api/chat` (RAG over a BUNDLED `rag_vector_db/` — no laptop, no docling, no
GPU). Retrieval reuses `chromadb.PersistentClient(path=str(DB_DIR)).get_or_create_collection(COLLECTION)`
then `col.query(query_texts=[q], n_results=...)`. Generation = same OpenRouter block
above, model from `OPENROUTER_MODEL` env (default `openrouter/free`).

### Bundle assembly (`deploy/build_deploy.py`)
```python
copy_tree(project_rag/web_ui,            deploy/web_ui)
copy_tree(project_rag_hybrid/rag_vector_db, deploy/rag_vector_db)  # ~10MB, 582 chunks
# cloud_server.py, render.yaml, Dockerfile, requirements.txt already in deploy/
```
`requirements.txt`: fastapi, uvicorn[standard], openai, chromadb, pyyaml.
`Dockerfile`: `FROM python:3.12-slim`, `COPY . .`, `CMD ["sh","-c","python cloud_server.py"]`.
`render.yaml` (free): type web, plan free, build `pip install -r requirements.txt`,
start `python cloud_server.py`, env `OPENROUTER_API_KEY` (secret, sync:false) +
`OPENROUTER_MODEL=openrouter/free` + `PORT=8000`.

## Verification (the SSE curl hang)
`curl -s -N -X POST .../api/chat` HANGS because the SSE stream stays open until
the client disconnects. Always bound it:
```bash
curl -s --max-time 30 -X POST http://127.0.0.1:8011/api/chat \
  -H "Content-Type: application/json" -d '{"question":"..."}' | head -c 400
```
Or read `-w "%{http_code}"` on a GET route. Confirmed: cloud server returned
`CLOUD_DEPLOY_OK` from bundled DB + OpenRouter with the key exported.

## Reality note for the user
"Runs when laptop is off" is ONLY satisfied by the cloud deploy. The laptop-hosted
site (ngrok + OpenRouter) is reboot-proof via `Agent_OS.cmd` but still needs the
laptop ON. State this plainly; don't over-promise.
