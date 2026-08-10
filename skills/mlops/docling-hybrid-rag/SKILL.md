---
name: docling-hybrid-rag
description: Build a local/hybrid RAG system that ingests PDFs with docling (DocumentConverter + HybridChunker), stores chunks in ChromaDB preserving heading metadata, and answers via a pluggable generator (local Ollama OR OpenRouter API) selected through a settings JSON. Use when the user wants a RAG app, wants docling specifically, or wants a provider-switchable (cloud/local) RAG.
---

# docling-hybrid-rag

Faithful pattern distilled from the user's `First_Rag.ipynb` + the `project_rag` /
`project_rag_hybrid` builds. The retrieval side is docling-only (do NOT substitute
PyMuPDF page text or a custom chunker — the user will reject it). Generation is
hybrid: local Ollama or OpenRouter, switched via `rag_settings.json`.

## When to use
- User says "build a RAG / use docling / make it hybrid (local + API)".
- Emphasize: docling for ingestion IS mandatory per this user; PyMuPDF is only used
  to split huge PDFs before docling, never as the text extractor.

## Pipeline (exact order)
1. **PyMuPDF** — only to split PDFs > N pages (default 8) into cached chunk PDFs
   under `rag_pdfs/temp_split_chunks/`. Caches on disk: skip re-split if chunk exists.
   Small PDFs (< N pages) pass through untouched.
2. **docling `DocumentConverter`** — `PdfPipelineOptions(do_ocr=True,
   generate_page_images=False, accelerator_options=AcceleratorOptions(num_threads=4,
   device=AcceleratorDevice.CUDA if torch.cuda.is_available() else CPU))`.
   `converter.convert(unit).document` -> markdown with layout.
3. **docling `HybridChunker`** — `HybridChunker(tokenizer=AutoTokenizer.from_pretrained(
   "sentence-transformers/all-MiniLM-L6-v2"), max_tokens=512, merge_peers=True)`.
   `chunker.chunk(dl_doc=doc)`. Each chunk has `chunk.text` and `chunk.meta.headings`
   (list of H1/H2 strings) — PRESERVE these.
4. **ChromaDB** — `PersistentClient(path="rag_vector_db")`,
   `SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")`,
   `metadata={"hnsw:space":"cosine"}`. Flatten `headings` -> `" > ".join(...)` for
   metadata (ChromaDB wants flat strings). Upsert in batches of 100.
5. **Generate** — retrieve top-3 chunks, build system prompt with context, stream answer.

## File structure (a project)
- `main.py` — pipeline + `ask_rag_system(question, collection, settings=None)` +
  `interactive_ui(collection, settings)`.
- `rag_settings.json` — `{configured, provider:"openrouter"|"ollama",
  openrouter_api_key, openrouter_model, ollama_model}`. First run prompts 1/2,
  saves file; subsequent runs skip the prompt. Edit file to switch providers later,
  or re-run with `--setup`.
- `setup.py` — deps: `PyMuPDF`, `docling`, `torch`, `transformers`,
  `sentence-transformers`, `chromadb`, and `openai` (hybrid only).
- `rag_pdfs/` — source docs. `rag_vector_db/` — persisted index (gitignore/omit from
  distributed builds).

## Hybrid generation (the switch)
```python
if provider == "openrouter":
    client = OpenAI(base_url="https://openrouter.ai/api/v1",
                    api_key=settings["openrouter_api_key"] or os.environ["OPENROUTER_API_KEY"],
                    default_headers={"HTTP-Referer":"https://localhost/rag",
                                      "X-Title":"Hybrid RAG"})
    stream = client.chat.completions.create(model=settings["openrouter_model"],
                                             messages=[...], stream=True)
else:  # ollama local
    stream = ollama.chat(model=settings["ollama_model"], messages=[...], stream=True)
```
Lazy-import `ollama` (set to None on ImportError) so the openrouter path works
without the ollama package installed.

## Dependencies / env
- `os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"]="1"` keeps Windows terminal clean.
- docling pulls RapidOCR/ONNX models on first run (one-time download).
- Local Ollama needs server up + model pulled.

## Web Deployment (your laptop = the server)
Turn the RAG into a public website backed by the LOCAL Ollama GPU model. Visitors
chat through a static HTML UI; requests are answered ONE AT A TIME (serial
queue) because an 8 GB VRAM card can't serve concurrent users. Reference skeleton:
templates/laptop_rag_server.py.

- FastAPI app; POST /api/chat returns StreamingResponse with
  media_type="text/event-stream". Each SSE frame is data: {"token": "..."}\n\n.
- Serialize generation with a deque + a single queue_worker() asyncio task.
  One answer at a time; others report their queue position and wait. This is the
  user's hard constraint: "1 user 1 prompt at a time, my GPU can't handle many."
- Offload the blocking ChromaDB disk read to loop.run_in_executor(...). Do NOT
  offload the Ollama stream (see Pitfalls - it breaks token extraction).
- ngrok tunnel opened/closed inside a FastAPI lifespan handler (no separate
  terminal). Paste auth token + free static domain into a private gitignored
  server_config.json. Without a token it still serves on localhost.
- Postgres (visitor_logs + waitlist tables) logs questions/answers/downloads
  ONLY while the laptop is on. If PG is down, set store.enabled=False and the
  site still works (logging skipped). This is the privacy rule: laptop off =>
  no visitor data can be stored.
- Downloadable "desktop app" = the hybrid project zipped WITHOUT rag_vector_db/
  and with a BLANK rag_settings.json (no API key). See Privacy note below.
- Copy template `templates/laptop_rag_server.py` as a starting point — it now
  includes query cleaning, the answer cache, the robust fallback prompt, AND the
  client-side double-submit guard (see the tail comment). Postgres owner-dashboard
  schema + daily-cron pattern: `references/dashboard_postgres.md`.

### Privacy model (MANDATORY for this user)
- Visitors only chat with YOUR local model against YOUR knowledge base.
- The downloadable hybrid app must contain NONE of your data or keys.
- A downloader's rag_vector_db/ and rag_settings.json are created fresh on
  their machine - they never see yours.
- Build the distributable zip: exclude rag_vector_db/, temp_split_chunks/,
  .venv, .env; ship a blank rag_settings.json + a FIRST_RUN guide page
  (create rag_pdfs/, set rag_settings.json, pick Ollama/OpenRouter).

## Verification (MANDATORY, real not mocked)
The first docling build is SLOW on CPU (OCR). Run the rebuild as a **background**
process and WAIT for it — never interrupt, because `process_rag_pipeline` calls
`client.delete_collection(...)` before upserting, so an interrupted run leaves an
empty/partial DB. Verify with:
- `TOTAL CHUNKS:` count printed, `=== DONE ===` reached.
- `query_test.py` against existing `rag_vector_db` answers a question.
- For OpenRouter, assert the request shape (model + messages roles) via a mock
  `OpenAI` lambda — no network needed.

## Pitfalls
- `do_ocr=True` required for scanned PDFs; it's slow on CPU. One bad_alloc on a huge
  PDF chunk is recoverable (docling continues) — don't kill the run over it.
- `transformers` warns "Token indices sequence length is longer than 512" — benign,
  it's docling's internal tokenizer, not your chunker.
- `chunk.meta.headings` can be `None` — guard it (`" > ".join(h) if h else "No Header"`).
- Don't skip `delete_collection` reset or old (non-docling) entries linger.
- Distributed/downloaded builds must strip `rag_vector_db/` and any cached
  `temp_split_chunks/` + clear `rag_settings.json` API key (privacy).
- OpenRouter key in plaintext settings file is a secret-hygiene smell; prefer
  `OPENROUTER_API_KEY` env var.

### CRITICAL: Ollama streaming token extraction (fastapi/async)
- `ollama.chat(model=..., stream=True)` returns a generator that MUST be iterated
  in the SAME thread that created it. Wrapping it in `asyncio.to_thread(ollama.chat,
  ...)` silently yields EMPTY tokens (the generation happens in the worker thread
  and is consumed there). Symptom: SSE stream connects, frames arrive, but every
  `{"token":""}` is empty. Fix: call `ollama.chat(...)` directly and iterate it
  synchronously in the coroutine (blocking is fine because the serial queue already
  runs one request at a time). Read tokens with `chunk["message"]["content"]`
  (dict access is robust on modern ollama `ChatResponse` objects; attr access also
  works). Skip empty pre-tokens (prompt-eval chunks before the model emits).
- Abliterated models (e.g. `qwythos-9b-abliterated`) REFUSE directive-style test
  prompts like "Reply with exactly: HELLO" and answer "I cannot complete this task."
  That looks like a streaming bug but isn't — test with a real KNOWLEDGE question,
  not a compliance/directive prompt. See scripts/verify_ollama_stream.py.

### CRITICAL: server restart / stale process on Windows
- On MSYS/git-bash, `pkill` is NOT available and `taskkill` needs `/PID` (not `//PID`).
  After editing the server, a stale `python server.py` may still hold port 8000, so
  your health check hits the OLD instance (e.g. `postgres:false` even after PG was
  fixed). Kill via `taskkill /PID <pid> /F`, confirm port free, then start fresh.

## Serving + hardening (real fixes from the live deploy)
These turned up when 1 user worked locally but the SAME request from a phone over
ngrok produced a garbled answer. Capture them — they will recur.

### Phone double-submit => merged streams bug
- Symptom: laptop sends one request, gets one clean answer. Phone (flaky mobile ->
  ngrok) RETRIES the POST, opening a SECOND /api/chat stream into the same chat box.
  The browser merges both answers into one bubble (real answer + fallback text).
- Server-side serial queue does NOT prevent this — each request is a separate stream.
- FIX (client UI): guard `send()` with a `_busy` flag + disable the send button while
  a request is in flight, so a retry is ignored. Always pass a `done` frame so the
  flag resets. (See templates/laptop_rag_server.py UI snippet / web_ui example.)

### Weak question phrasing misses retrieval => false "I don't have info"
- Symptom: "Can u say what is calude leaked files" returned the fallback even though
  the right chunk existed, because filler words ("can u say what is") poisoned the
  vector query. A reworded question found it.
- FIX: strip filler before retrieving. `_clean_query(q)` lowers, drops a stopword
  set (can/u/you/say/what/is/the/a/of/...), and searches on the remainder. Bump
  `n_results` 3 -> 5. Retrieve 5, build context from all 5.
- FIX (prompt): don't tell the model to emit the fallback phrase whenever it's unsure.
  Instead: "answer from CONTEXT; only say you lack info if context is genuinely empty."
  And when `had_context` is False (zero chunks), send a hard prompt that replies
  EXACTLY with the "no info" sentence — stops the model guessing from outside
  knowledge. This is the privacy-critical rule: the local model must NOT answer from
  its own training data when the KB is empty.

### Answer cache (smooths multi-user load)
- A dict keyed on `_clean_query(q)`, TTL 1h. On a hit, return the cached answer as a
  single `token` frame + `done` — instant, no GPU. Cache the FULL assembled answer at
  the end of a real generation (`_cache_put`). Under a 20-user burst, repeat/similar
  questions collapse to cache hits, so the serial GPU queue only pays once.
- Keep it in-memory (simple); it's a laptop server, not a cluster.

### Owner dashboard + daily snapshot (telemetry from Postgres)
- `/dashboard` route, **localhost-only** (reject non-127.0.0.1/`::1`/`localhost` with
  403). Reads `store.today_stats()` from Postgres: events today, questions today,
  waitlist total, recent activity rows, waitlist rows. Render a simple Tailwind HTML
  table (no auth — owner-only by IP).
- Daily cron: a no-agent script job that runs `dashboard_daily.py` (wrapper in
  `~/.hermes/scripts/` invoking the project script). Snapshots the day into
  `dashboard_log/dashboard_YYYY-MM-DD.md` + `.json` and delivers a one-line summary.
  MUST handle Postgres-off gracefully: write a "no data (laptop off?)" snapshot and
  exit 0 — never crash.
- Hermes cron quirk: `script` must be a bare filename under `~/.hermes/scripts/`; an
  absolute path is rejected. Use a thin wrapper there that calls the real project
  script (the project script hardcodes its own PROJECT_DIR).

### Concurrency truth (verified)
- Fired 20 simultaneous requests against the serial queue: all 20 answered with real
  text (fail=0) in ~98s. The "GPU can't serve many users" worry is handled by the
  serial queue + cache: each user is answered in order, no crash, no wrong answer.
  Capacity = throughput of one local model call; cache turns repeated questions free.

### ngrok authtoken vs API key (gotcha)
- The token the user pastes from ngrok is an **authtoken** (connects tunnels). It is
  NOT an API key. Reserving a *static domain* needs a separate API key from
  dashboard.ngrok.com/api-keys. Without it, the free URL works but changes every
  restart. Don't burn time hitting the reserved_domains API with the authtoken — it
  returns ERR_NGROK_206. Ask the user for the API key only if they want a fixed URL.
