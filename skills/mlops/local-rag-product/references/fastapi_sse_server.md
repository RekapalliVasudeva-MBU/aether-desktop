# FastAPI SSE server (project_rag website) — proven skeleton

Run: `python server.py` (uvicorn inside `if __name__`). Laptop is the server.

## Key parts
- **Serial queue** (`deque` + `asyncio.Lock` + one `queue_worker` task):
  - client enqueues `{"question","session_id","enqueue":q.put}`; gets a `queued`+`position` frame.
  - worker: `async for piece in generate_rag_stream(...): await item["enqueue"](piece)`,
    then `await item["enqueue"](None)` to signal end.
- **SSE generator** `generate_rag_stream(q, sid)`:
  1. answer cache check (keyed on cleaned query) -> return instantly if hit.
  2. `clean_q = _clean_query(q)` (strip "can u say/what is/...") -> `collection.query(n_results=5)`.
  3. build system prompt; if ZERO chunks -> "I don't have information...".
  4. `ollama.chat(model, messages, options={"keep_alive":"-1"}, stream=True)` — MUST iterate
     the generator in the SAME thread (do NOT wrap in asyncio.to_thread -> empty tokens).
     Read tokens via `chunk["message"]["content"]`.
  5. yield `data: {"token": tok}\n\n` ... then `data: {"done": true}\n\n`.
  6. cache full answer; log question+answer to Postgres.
- **ngrok lifespan** (in `lifespan`): `from pyngrok import ngrok; ngrok.set_auth_token(token);
  ngrok.connect(port)` or `ngrok.connect(port, domain=domain)` if a static domain (paid only).
- **Postgres** `VisitorStore`: connect in try/except -> `enabled=False` if down (site still works).
  `today_stats()` for `/dashboard`. Tables: `visitor_logs(session_id,project,event,detail,ts)`,
  `waitlist(name,email,note,ts)` with `ON CONFLICT (email) DO UPDATE`.
- **Health**: `{"status","chunks":collection.count(),"queue_position","current_request",
  "gpu_model","postgres":store.enabled}`.
- **Download**: serve `dist/project_rag_hybrid.zip` (FileResponse). Log `download` event.
- **/dashboard**: localhost-only (check `request.client.host in ("127.0.0.1","::1")`), render
  today's stats from `store.today_stats()`.

## Pitfalls
- Do NOT set `Connection: keep-alive` on SSE responses (WSGI AssertionError).
- Killing a stale server: on Windows use `taskkill /PID <pid> /F` (no `pkill` in MSYS).
  Old instance may keep port 8000 and hide new config — always confirm port is free.
- Abliterated model refuses directive prompts ("Reply with X"); test with real questions.
