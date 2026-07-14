# AetherMind — 24/7 Cloud Deploy

The laptop-dependent site at `project_rag/server.py` is OpenRouter-powered (no
GPU) but still needs the laptop to be ON. To satisfy "site must run even when
my laptop is off", deploy this bundle to a **free** cloud host.

## What's inside
- `cloud_server.py` — FastAPI server: serves `web_ui/` + `/knowledge` + `/api/chat`
  (RAG over the bundled `rag_vector_db/`), all via OpenRouter.
- `web_ui/` — your premium UI (copied from project_rag).
- `rag_vector_db/` — 582-chunk knowledge base (copied from project_rag_hybrid).
- `requirements.txt`, `Dockerfile`, `render.yaml`.

## Deploy (Render free tier — 0 USD)
1. `python deploy/build_deploy.py`  (assembles the bundle)
2. Push `deploy/` to a GitHub repo.
3. render.com → New → Blueprint → pick the repo.
4. Add secret env var `OPENROUTER_API_KEY = <your key>`.
5. Deploy → live on `https://aethermind.onrender.com` forever.

## Alternative: Hugging Face Spaces
- Create a Space (Docker SDK).
- Upload `deploy/` contents (Dockerfile at root).
- Set `OPENROUTER_API_KEY` in Space secrets.

## Update the knowledge base
Re-run the project_rag_hybrid ingestion, then `python deploy/build_deploy.py`
and re-deploy.
