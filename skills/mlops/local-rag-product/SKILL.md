---
name: local-rag-product
description: Build, deploy, and productize a local RAG system as a laptop-hosted website + downloadable self-hosted desktop app (docling pipeline, FastAPI SSE server, ngrok tunnel, Postgres visitor logging, pywebview desktop UI, installer, daily dashboard). For this user's AetherMind project and similar local-RAG productization.
---

# Local RAG Product (website + downloadable desktop app)

## When to use
User wants a RAG system turned into a shippable product: a website served from their
laptop (the "server") AND a downloadable desktop app others run on their own machines
with their own PDFs/keys. Covers deployment, tunneling, desktop packaging, privacy, and
lightweight modern UI.

## Architecture (proven for this user)
- **project_rag = website**: FastAPI `server.py` + `web_ui/index.html`. Laptop is the
  server. Serves chat UI, streams answers over SSE, **one request at a time** (serial
  queue — GPU can't serve many). Public URL via a reverse tunnel (ngrok OR cloudflared — obey the provider the
 user names in the current instruction; see the decisive-preference pitfall below). Postgres
  logs visitors/waitlist ONLY when laptop on (graceful off). `/dashboard` localhost-only.
  Daily snapshot via Hermes cron.
- **project_rag_hybrid = downloadable app**: `main.py` docling pipeline + `desktop/`
  (pywebview `desktop_app.py` + bottle `api_server.py`). `install.py` asks permission
  then `pip install -r requirements.txt`. Ships blank `rag_settings.json`; NEVER ships
  owner's `rag_vector_db/` or key.

## Hard rules for this user
- **Privacy-by-design**: downloadable zip = code only. Exclude `rag_vector_db/`, real
  `rag_settings.json` (write a blank one). Downloaders never see owner data.
- **Free tier only**: free models, free ngrok (no paid static domain). Don't propose paid tiers.
- **Lightweight UI, but GO FULL INTERACTIVE**: Spline-community aesthetic (glass +
  floating gradient orbs + smooth motion) AND the user explicitly wants the
  premium "living" feel — cursor-reactive `<canvas>` particle field, a cursor-glow
  that tracks the pointer, and magnetic buttons that lean toward the cursor on hover.
  He said "I need this UI no matter what" after earlier warning "don't do anything
  crazy / less complex yet beautiful". Resolution: deliver the interactive motion (it IS
  what he considers beautiful) but keep it dependency-free (raw canvas 2D + CSS, no
  three.js/WebGL bundle, ~90 particles, capped DPR<=2). Apply the SAME motion layer to
  BOTH the web UI and the desktop UI so they match. See `templates/interactive_bg.html`.
- **Simple > over-engineered** (applies to backend/logic, not visual polish — the user
  will trade simplicity for a more impressive UI).
- **Installs permitted** (install whatever you want) for this project; still confirm
  before ollama model pulls / large downloads.
- **Citation display**: user explicitly requested PDF sources be HIDDEN in chat UI
  (both web and desktop). Frontend citation rendering is commented out; backend still
  returns citations but UI no longer shows "📚 Sources:". See `references/debugging_session_2026-07-25_afternoon.md`.
- **USER WORKFLOW RULE (repeat offender — embed it):** the user repeatedly and emphatically
  says: make it simple, don't make it too complicated; if your approach fails, ASK ME which
  approach to take; don't over-complicate / don't hallucinate; and wants a plain
  working / broken / pending status report, not process narration. Operationalize this:
  * Prefer the SIMPLEST fix that makes the feature work; stop stacking exotic workarounds.
    (Example that earned a scolding: chasing PyInstaller --collect-all / --exclude /
    stub-file rabbit-holes for chromadb's hnswlib — the right simple move was to patch the
    ONE source line that hard-imports hnswlib in build_venv and let chromadb fall back to
    its Rust API.)
  * If you try an approach and it fails, do NOT silently loop on variations. After 1-2
    failed attempts, STOP and ask the user to pick an approach (offer 2-3 concrete options)
    OR report working/broken/pending and hand off the unsolvable part. Never hallucinate a
    green result.
  * When you finish a multi-step task, lead with: what WORKS (verified), what is BROKEN or
    unverified (and who should check it), what is PENDING. One response, no filler.
  * DIRECT IMPERATIVES: when the user issues a blunt command ("strictly obey my command",
    "fix this now", "add the sessions panel"), execute it COMPLETELY — do not under-deliver,
    substitute a partial fix, or re-ask for confirmation on low-stakes execution. He equates
    a silent gap with "the app can't do basic tasks". If a prerequisite is genuinely missing,
    state it once and proceed with the safest default.
  * SHOW THE WORK: he wants to SEE the agent think, call tools, and reflect — a live timeline
    (see `references/aether_execution_animation.md`), NOT a blank wait that ends in a bare
    answer. A chat that returns only the final text reads as "broken" to him.
  * FUSE INSIGHTS, don't feature-paste: when he points you at a source (a PDF, a repo, a
    Hermes pattern) and says "make it optimized/intelligent", read it and merge its concrete
    techniques with the existing codebase — e.g. the Claude Code leak PDF -> two-layer
    compaction + 32KB tool cap + step-event streaming.

## Critical techniques & pitfalls (verified this session)
- **FastAPI `FileResponse` caching**: serving `index.html` via `FileResponse` sends
  `ETag` + `Last-Modified` and NO `Cache-Control`. Browsers cache the SPA shell and
  keep showing the OLD UI even after you edit the HTML. ALWAYS override the response
  headers on the `/` route:
  ```python
  resp = FileResponse(idx)
  resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
  resp.headers["Pragma"] = "no-cache"
  resp.headers["Expires"] = "0"
  return resp
  ```
  Symptom we hit: ngrok returned byte-identical NEW HTML but the user still saw the old
  design — it was client cache, not a server error. After this fix, a hard-refresh
  (Ctrl+Shift+R) shows updates. The `/ui` StaticFiles mount has the same risk for
  assets; if live UI edits don't show, add `Cache-Control: no-store` there too.

- **Azure Container Apps deployment (serverless, cost-optimized for this project)**: This
  is the recommended cloud target when the laptop-hosted site needs to run 24/7 without the
  laptop on. Key decisions (verified this session):
  * **Container Apps** (not App Service, not VM) — scales to zero (min-replicas=0), pay
    only when handling requests, ~$5-15/month for low traffic vs $50+ for App Service.
  * **GitHub Actions + OIDC federated identity** — no secrets in GitHub, no service
    principal password. App Registration → Federated Credential (GitHub Actions scenario) →
    Role Assignment (Contributor on resource group).
  * **Multi-stage Dockerfile** — builder stage installs deps in venv, runtime stage copies
    venv + only runtime system deps (`libgl1`, `libgomp1`, `libpq5`, `ca-certificates`).
    Uses CPU-only torch (`--index-url https://download.pytorch.org/whl/cpu`) to avoid CUDA
    bloat. Gunicorn with 1 worker, preload, max-requests=1000 for memory stability.
  * **Pinned requirements with upper bounds** — per supply-chain policy (AGENTS.md):
    `docling==1.20.0`, `chromadb==0.6.3`, `rich<14.0.0,>=13.7.0` (docling dep conflict),
    `torch>=2.0.0,<3 --index-url https://download.pytorch.org/whl/cpu`.
  * **Health endpoints** — `/healthz` (liveness, no DB), `/api/health` (readiness, with
    queue status). Container Apps uses `/healthz` for liveness probe.
  * **Graceful shutdown** — SIGTERM/SIGINT handler sets global flag, lifespan context
    manager logs shutdown.
  * **Configurable ChromaDB path** — `CHROMA_DB_DIR` env var (default `./rag_vector_db`),
    mount Azure Files volume for persistence across cold starts (re-ingest on cold start
    otherwise).
  * **GitHub Actions workflows** — `build-push.yml` (build → test → push to GHCR),
    `deploy-azure.yml` (deploy Container App, update image, verify health). Both use
    OIDC `azure/login@v2` with federated credentials.
  * **Portal steps for user** (no CLI):
    1. Resource Group → Create
    2. App Registration → New → Federated Credential (GitHub Actions, org/repo/branch:main)
    3. Enterprise Applications → Verify SP → Access control (IAM) → Contributor on RG
    4. Subscriptions → Copy Subscription ID
  * **Secrets in GitHub** — AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID,
    OPENROUTER_API_KEY, RAG_GITHUB_REPO/PATH/REF, optional RAG_PG_DSN + Log Analytics.
- **SSE via bottle**: do NOT set `Connection: keep-alive` — WSGI raises
  `AssertionError: Hop-by-hop header not allowed`. Set
  `bottle.response.content_type="text/event-stream"` + `Cache-Control: no-cache` only;
  return the generator directly (not wrapped in `HTTPResponse`).
- **pywebview + FastAPI: server MUST start in a thread BEFORE webview** — the UI
  loads `http://127.0.0.1:<port>/ui/`; if uvicorn isn't already serving, the window
  shows a dead URL. Correct pattern (verified this session):
  ```python
  def _serve(): uvicorn.run(app, host="127.0.0.1", port=port)
  threading.Thread(target=_serve, daemon=True).start()   # start server FIRST
  import webview
  webview.create_window("Aether", url=url, width=1100, height=800)
  webview.start()                                      # webview.start() on MAIN thread
  ```
  `webview.start()` still must run on the main thread (else "pywebview must be run on
  a main thread"). On Windows it uses built-in Edge WebView2 (no Chromium download).
  If `webview` import fails (headless), fall back to keeping the uvicorn thread alive
  and tell the user the server is at `url`.
  **CRITICAL for this user:** the native pywebview window is the REQUIRED primary UI —
  do NOT make a "open in browser" tab the default (the user rejected that: "u again fixed
  it to local host website"). WebView2 is present on his machine; the earlier silent
  no-window was the launch pattern, not missing WebView2. Packaging + icon + stale-port
  pitfalls for this are in the `windows-desktop-app-packaging` skill (native-window-primary
  section).
- **Serial one-at-a-time queue**: `deque` + `asyncio.Lock` + single `queue_worker` task.
  Clients get a `queued` + `position` frame. Prevents GPU overload under many users.
- **Answer cache**: key on a cleaned query (`_clean_query` strips filler words like
  "can u say"/"what is" so weak phrasings still match retrieved chunks). Returns cached
  answer instantly — smooths repeated questions under load (verified: 20 concurrent
  users -> all 20 answered, fail=0, in ~98s).
- **Retrieval quality**: clean filler words before `collection.query`; retrieve
  `n_results=5`; only say "no info" when ZERO chunks retrieved. Abliterated local model
  refuses directive test prompts — test with REAL knowledge questions, not "Reply with X".
- **Hybrid retrieval (current build)**: the user's "Master Approach" = dense vector
  (ChromaDB) + BM25 (`rank_bm25`) + RRF (k=60) + LOCAL CrossEncoder rerank
  (`cross-encoder/ms-marco-MiniLM-L-6-v2`) + rule router (`"page N"` -> page fast-path)
  + RBAC (`access` tag) + fit_context (26K char cap). Implemented in BOTH `server.py`
  and `desktop/api_server.py`. KEEP/DROP guard prevents bloat (no FAISS/bge-m3/LLM
  router/Whoosh/Tantivy). Full condensed pattern + the two plan bugs fixed in
  `references/hybrid_retrieval.md`. Rebuild BOTH ChromaDBs after changing ingest
  metadata (docling takes ~10 min / 25 PDFs, run in background).
- **Incremental upload → live collection (chat "📎 add file")**: visitor attaches a PDF;
  `main.chunk_single_pdf` reuses the SAME docling converter + HybridChunker, stored under
  `rag_pdfs/temp_split_chunks/`, then `collection.upsert` (APPEND, never wipe) + rebuild
  BM25 so hybrid search sees it immediately. Mirrored in `desktop/api_server.py`. Full
  pattern + the BM25-rebuild gotcha + PyMuPDF probe-PDF verification in
  `references/hybrid_retrieval.md` (section "Incremental upload → live collection").
- **RERANKER SORT BUG**: never `sorted(zip(scores, docs, metas), reverse=True)` — on
  tied scores it compares `metas` (dicts) and crashes with `'<' not supported between
  dict and dict`. This latent bug fired the moment an upload added enough chunks to create
  ties. FIX: `sorted(zip(scores, docs, metas), key=lambda x: x[0], reverse=True)`.
  Detail + reproduction in `references/hybrid_retrieval.md` (pitfall #5).
- **Two plan bugs to NOT repeat** (from `references/hybrid_retrieval.md`): (1) docling
  >=0.5 page path is `chunk.meta.doc_items[0].prov[0].page_no`, NOT `chunk.meta.page_no`;
  (2) reranker model is `cross-encoder/ms-marco-MiniLM-L-6-v2`, NOT
  `sentence-transformers/ms-marco-MiniLM-L-6-v2` (404).
- **docling is slow on CPU** for large PDFs; pre-split with PyMuPDF into <=8-page chunks
  (cached to disk). On this user's RTX 5070, docling uses CUDA automatically.
- **ngrok free tier = BANDWIDTH CAP (this session, hard-won)**: the free plan has a
  monthly bandwidth quota. Serving the **135 MB installer through the tunnel** burned it in
  one day → `ERR_NGROK_725 Network bandwidth exceeded`, and downloads failed with
  "Couldn't download — No permissions" (browser appended `.txt` to the dead tunnel). The
  reserved static domain (`marshy-ancient-rebuild.ngrok-free.dev`) survived restarts but the
  tunnel was unusable once the quota hit zero. LESSON: ngrok free is fine ONLY for light UI
  traffic — never proxy a large binary through it.
- **USER TUNNEL PREFERENCE IS DECISIVE — BUT THEY CAN OVERRIDE IT PER-TASK (corrected this session)**:
  The user's **stated** tunnel preference wins — when he names a service, USE THAT
  ONE, do NOT substitute another (he reads a silent swap as "you didn't obey my
  command"). BUT note the correction from this session: his *standing* preference
  was "ngrok, not cloudflared", yet when the ngrok tokens kept failing he
  explicitly said "use this cloudflare" and overrode it. So the rule is:
  **obey the provider named in the CURRENT instruction.** If he says "use ngrok"
  use ngrok; if he later says "use cloudflare" use cloudflare. Do NOT keep citing
  an old standing preference against a new explicit instruction in the same thread.
  He also rejected `localhost.run` by NAME ("not localhost, I need a real website
  link") even though localhost.run produces a public `https://*.lhr.life` URL — the
  word "localhost" in the tool name read as "local-only" to him. Lesson: when a
  user rejects a tool by name, don't re-propose the same tool; pick a differently
  named one (cloudflared/ngrok) or explain the URL is public. The bandwidth-cap
  caveat still applies (don't proxy the big installer through the tunnel — serve it
  from the website's `/download/*` route or redirect to a GitHub Release asset).
- **CLOUDFLARE QUICK TUNNEL NEEDS NO TOKEN (this session, useful fallback)**:
  When ngrok tokens fail and the user approves Cloudflare, `cloudflared` can open a
  public tunnel with ZERO credentials — no API token, no login:
  ```bash
  # download official binary (permitted when user says "make it live / do whatever")
  curl -sL -o cloudflared.exe https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
  # start a quick tunnel (random URL, regenerates each restart, NO auth needed)
  ./cloudflared.exe tunnel --url http://localhost:8000
  ```
  The public URL prints as `Your quick Tunnel has been created! Visit it at:
  https://<random>.trycloudflare.com`. VERIFIED LIVE this session: the URL returned
  200 and served the real site from a fresh-user browser. Caveats: (1) the URL is
  RANDOM and changes every time the tunnel restarts — not stable; (2) for a FIXED
  URL that survives reboots, use a named tunnel (`cloudflared tunnel create <name>`
  + a valid Cloudflare API token) and run it as a Windows service. (3) git-bash
  `cmd /c "C:\\path\\cloudflared.exe"` rewrites the path to `C:\\c\\...` (see the
  path-doubling quirk in `windows-app-launch-debug`); call the exe via Python
  `subprocess` or a `.ps1` instead.
- **VERIFY THE TUNNEL CREDENTIAL BEFORE BURNING CYCLES (this session, high-value)**:
  Before announcing "site is live", actually start the tunnel and read its auth result.
  ngrok rejects a bad token with `ERR_NGROK_107` — *"The authtoken you specified is
  properly formed, but it is invalid"* — meaning it was **reset, revoked, or the account was
  left/removed**. A token that's "properly formed" still fails if it's stale. The user may
  paste an OLD/revoked token (this session he pasted two revoked ngrok tokens, then labeled
  one "authtoken" and one "api key" — BOTH were invalid). Rules:
  * **Agent authtoken ≠ API key.** The *agent authtoken* (`ngrok config add-authtoken <tok>`)
    is what OPENS tunnels. The *REST API key* (`Authorization: Bearer` against `api.ngrok.com`)
    is for account automation only and CANNOT start a tunnel. Testing an agent authtoken via
    the Cloudflare API (or via `api.ngrok.com` with a Bearer header) returns 403/404 and tells
    you nothing about tunnel capability — test it the way the agent uses it: `ngrok config
    add-authtoken <tok>` then `ngrok http 8000` and watch for `ERR_NGROK_107`.
  * **Don't loop on a failing token.** After 1-2 auth failures, STOP and tell the user the
    token is invalid/revoked and ask them to paste a FRESH one from
    https://dashboard.ngrok.com/get-started/your-authtoken. Never fabricate a "live link".
  * **Downloading the binary is permitted** when the user says "do whatever / make it live"
    (overrides the usual no-download-without-confirmation for that grant). Official binary:
    `curl -sL -o ngrok.zip https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip`
    then `unzip -o ngrok.zip`. Put `ngrok.exe` in a stable path (e.g. `C:\\Users\\valte\\ngrok.exe`).
  * **Get the live URL** from the local API: `curl -s http://127.0.0.1:4040/api/tunnels` →
    `public_url` (note: MSYS `curl` can return 0 bytes for the ngrok TLS URL — use
    `python -c "urllib.request.urlopen(...)"` for reliable checks).
  * **cloudflared leftover note:** if you DO fall back to cloudflared, the named tunnel's
    binary + `~/.cloudflared/*` can get deleted from disk while a zombie service lingers —
    the tunnel then has NO recoverable URL and won't survive a reboot. Prefer ngrok per the
    user's standing instruction above.
- **ngrok free domain stability (still true, but secondary)**: a STATIC domain CAN be
  reserved on the free plan and survives restarts (does NOT change per restart). Authtoken
  != API key. But given the bandwidth cap, treat ngrok as a fallback for light UI traffic,
  not the primary tunnel for a download-bearing site. Verify tunnel state:
  `curl -s http://localhost:4040/api/tunnels` → `public_url`.
- **ngrok restart lock (`ERR_NGROK_334` / public 502 after a server restart)**: when you
  kill the website server and relaunch `python server.py`, the OLD ngrok tunnel endpoint
  stays "online" in ngrok's **cloud** for a short grace period even after the local ngrok
  agent dies. The new server then fails to bind the static domain and the public URL
  returns **502** — but local `:8000` is fine (200). Symptom in server log:
  `ERR_NGROK_334 ... endpoint already online`. FIX: kill ALL `ngrok.exe` processes
  (`tasklist | findstr ngrok` → `taskkill /PID <pid> /F`) AND the old server PID, then
  wait ~30–60s for ngrok cloud to release the endpoint before relaunching. If the server
  printed `Public URL: https://...ngrok-free.dev` at startup, the bind SUCCEEDED — a 502
  then means a STALE server is still holding port 8000, not a tunnel issue:
  `netstat -ano | findstr :8000` shows the real listener PID; kill it, wait for cooldown,
  relaunch ONE server. Don't conclude the site is down from the 502 alone — local curl on
  `:8000` returns 200; only the public tunnel is locked.
- **Service MUST survive reboots (the #1 outage cause)**: a server/ngrok started as a chat
  background process dies when the laptop reboots or the session ends — the site goes dark
  and "turn on the laptop → works" is FALSE unless something auto-starts them. FIX: add an
  idempotent auto-start to `Agent_OS.cmd` in the Windows **Startup** folder
  (`%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup`). Pattern:
  ```bat
  @echo off
  cd /d C:\\Users\\valte\\agent-os
  start /min "" npx next start -p 3001
  SET PROJ=C:\\Users\\valte\\project_rag
  netstat -an | findstr ":8000 " | findstr "LISTENING" >nul || (
    start /min "" cmd /c "cd /d %PROJ% && python server.py >> \"%PROJ%\\server_run.log\" 2>&1"
  )
  tasklist | findstr /i "ngrok.exe" >nul || (
    start /min "" cmd /c "cd /d %PROJ% && ngrok http 8000 >> \"%PROJ%\\ngrok_run.log\" 2>&1"
  )
  ```
  The `netstat`/`tasklist` guards make it idempotent (re-run safe, no duplicate procs).
  Task Scheduler (`schtasks /Create /SC ONLOGON`) needs admin (was denied) — Startup folder
  is the no-admin path and is sufficient for per-user logon. First boot needs ~30–60s for
  ChromaDB+reranker to load before the site answers. After this fix, reboot-and-it-works
  actually holds. See `references/autostart_windows.md`.
- **OpenRouter conversion (no GPU, portable)**: replace local Ollama in `server.py`
  with OpenRouter's OpenAI-compatible SSE stream (base_url
  `https://openrouter.ai/api/v1`, model default `openrouter/free`). Read the key
  from `OPENROUTER_API_KEY` env / `openrouter_api_key` config / the app's OWN
  `.env` under AETHER_HOME. `openrouter/free` IS free — don't false-warn (see
  `:free` check quirk in `references/openrouter_cloud_deploy.md`). Verified:
  `POST /api/chat` returns real tokens; public ngrok URL 200.
- **DISTRIBUTABLE AGENT APP — API-KEY LEAK (this session, blocker-class)**:
  When the product becomes a *downloadable agent app* (not just the laptop-hosted
  site), the code MUST NOT read the developer's personal key or hardcode their
  username. The bug we shipped + fixed this session: `get_api_key()` scanned a
  hardcoded `C:\\Users\\valte\\AppData\\Local\\hermes\\.env` and
  `skills.copy_user_skills()` hardcoded `C:\\Users\\valte\\...` paths — so any user
  who downloaded the app would pull the dev's real OpenRouter key out of the dev's
  machine path. Correct pattern: key resolves ONLY from `OPENROUTER_API_KEY`
  env OR the agent's OWN `<AETHER_HOME>/.env` (written by `doctor --fix`,
  never a sibling app's file). `doctor --fix` writes to `<AETHER_HOME>/.env`,
  NOT hermes's. Remove ALL `valte`/username literals; use `os.environ`/`AETHER_HOME`.
  Verify with: `grep -rn "valte\\|hermes .env\\|hermes\\\\.env" aether/` → must be CLEAN.
  For the dev's own machine only, seed `<AETHER_HOME>/.env` once from your
  personal key (out-of-band) so it works without leaking in source. Full pattern +
  the dead-tool-loop fix below in `references/aether_agent_app.md`.
- **True 24/7 = cloud deploy (laptop OFF)**: the laptop-hosted site is
  reboot-proof but still needs the laptop ON. To satisfy "site runs even when my
  laptop is off", bundle a self-contained cloud server (`deploy/cloud_server.py`
  + copied `rag_vector_db/` 582 chunks + `web_ui/`) and deploy free
  (Render Blueprint `render.yaml` / HF Spaces Docker). The cloud server does
  RAG over the BUNDLED DB via OpenRouter — no laptop, no GPU, no docling.
  Verified locally: returned `CLOUD_DEPLOY_OK` from bundled DB. Assembly +
  patterns + the SSE `curl` verification hang in
  `references/openrouter_cloud_deploy.md`.
- **AGENT TOOL-LOOP WAS DEAD — PITFALL (this session, high-value)**: building an
  OpenAI-style tool-calling agent is useless unless you actually pass the schemas to
  the model. The bug we shipped + fixed: `run_agent` computed `schemas =
  tool_schemas()` but called `provider.chat(messages, ...)` **WITHOUT `tools=schemas`** —
  so the model never emitted `tool_calls` and `call_tool` never ran (the whole
  agent was a no-op talking to itself). FIX: `provider.chat(...)` must accept
  `tools` + `tool_choice="auto"` and `run_agent` must pass the merged
  `get_external_tool_schemas()` (built-in + MCP tools) on EVERY call. VERIFY the
  loop is live with a real execution test, not just an import check — see
  `references/aether_agent_app.md` (the calculator test).
- **PROVE THE AGENT USES TOOLS (don't trust imports)**: an import-success or
  "schemas=[terminal,read_file,...]" print is NOT proof. Run a self-contained
  task that REQUIRES tool use and assert the side effect on disk: e.g. ask the agent
  to "use terminal to create `cal_project/`, write `calculator.py` with add/sub/mul/div
  (div guards zero), then RUN it via terminal and verify output". Then read the
  written file + `os.walk(cal_project)` to confirm it exists + the run happened.
  This session: agent created `cal_project/calculator.py`, ran it
  (`add(2,3)=5`, `sub(10,4)=6`, `mul(6,7)=42`, `div(20,5)=4.0`), stored it
  on the laptop. One test proves tools + skills-preload + terminal control + file
  write + real project storage all work. Pattern in `references/aether_agent_app.md`.
- **Local HTTP checks via curl**: `curl -s -N` on an SSE POST HANGS (stream
  stays open). Bound it with `--max-time 30 ... | head -c 400`. For plain
  status use `-w "%{http_code}"` on a GET. (MSYS `curl` ngrok TLS also returns
  0 bytes — use `python -c "urllib.request.urlopen(...)"` for reliable checks.)
- **Double-submit guard (UI)**: disable send button + `_busy` flag while a request
  streams — phone flaky connections retry POSTs and would merge two answers into one
  bubble.
- **Local HTTP checks on this host**: `curl` through MSYS/git-bash returns 0 bytes for
  the ngrok TLS URL (`HTTP 200 0B`) — unreliable. Use `python -c "urllib.request.urlopen(...)"`
  for reliable status/size checks, or PowerShell `Invoke-WebRequest`. Don't conclude a
  site is down from a 0-byte curl.
- **Browser backend is unavailable here** (`net::ERR_ABORTED` on every navigation, even
  example.com) — cannot open external sites (chaingpt.org, codedesign.ai) to copy their
  exact design. Build the described interactive style from scratch; ask the user to paste
  exported HTML/screenshot if pixel-matching is required. Do NOT claim to have viewed a
  site you couldn't open.
- **"What this model knows" page (set visitor expectations):** visitors don't know what
  questions the RAG can answer. Add a SEPARATE route `/knowledge` (its own HTML page,
  linked from the nav) that maps the indexed knowledge into 3-4 topic areas, each with
  3 real, use-case-style example questions (NOT generic what-is-RAG prompts — model the
  user's own KARLA example: "walk through a real production example: how would X-style
  retrieval be wired into a support bot, and where does it get used?"). Implementation
  recipe (verified this session):
  * Top-LEFT of the page: a **Download Guide** button = an `<a href="/api/knowledge-guide"
    download="AetherMind-Knowledge-Guide.md">`. The route returns the same content as a
    markdown `StreamingResponse` with `Content-Disposition: attachment` — so visitors can
    save what the model knows offline.
  * The chat box stays on `/` (don't hide it). Make example questions clickable:
    `onclick` stores the text in `sessionStorage` (`aether_pending_q`) and navigates to
    `/`; the chat page reads it on load and prefills the input. Zero backend coupling.
  * Ground the example questions in the ACTUAL PDFs — list `rag_pdfs/` to see real topics
    (RAG fundamentals, vector DBs, agentic RAG, agent memory, MCP, production RAG) before
    writing questions. Don't invent topics the KB doesn't cover.
  * Add the `/knowledge` and `/api/knowledge-guide` routes in `server.py` next to the
    static-UI block; set `Cache-Control: no-store` on `/knowledge` like `/`.
- **`gh` CLI auth mismatch across shells (Windows)**: the user ran `gh auth login` in
  **PowerShell**, but the agent's terminal runs in a **separate bash/MSYS** env — `gh auth
  status` there still reported "not logged in" even though the browser flow completed. The
  token IS stored under the Windows user profile and IS reachable; the CLI's own host-key
  check was just confused. FIX (no re-login needed): recover the token and export it in the
  agent shell so `gh` uses it directly:
  ```bash
  export GH_TOKEN=$(gh config get -h github.com oauth_token 2>/dev/null)
  gh auth status        # now shows "Logged in ... (GH_TOKEN)"
  ```
  Then `gh repo create ... --public` / `gh repo view` work. `export` persists for the rest
  of the agent session. Verify with `gh api user --jq .login`. (Also applies: the agent
  shell's HOME may differ from PowerShell's, so `~/.config/gh` lookups can miss the token
  file — `GH_TOKEN` sidesteps that entirely.)
- **GitHub repo hygiene for this project**: push the two repos PRIVATE-by-default per the
  user's standing rule (this session he granted a one-time public exception). Always
  `.gitignore` `.env`/`*.env`/`auth.json`/`credentials.json`/`dist/*.exe`/`*.zip`/
  `rag_vector_db/`/`rag_pdfs/`/`session_backups/`/`*.log`/`nul` BEFORE the first `git add`.
  Run a secret sweep on staged files before pushing: `git diff --cached --name-only |
  xargs grep -lI -E "sk-or-[A-Za-z0-9]{20,}|OPENROUTER_API_KEY\\s*=|NGROK_AUTH[A-Z]*\\s*="`
  must return NOTHING. Env-var *names* referenced in code (e.g. `os.environ.get("OPENROUTER_API_KEY")`)
  are fine — only real key VALUES are leaks. The desktop app must never read a sibling
  app's `.env` or hardcode the username (see API-KEY LEAK pitfall). Point README users to
  the live site for the download; keep the installers OUT of git (serve via the website's
  `/download/*` routes instead).
- **Desktop app: Hermes-style sessions** (per-conversation history in the frozen app):
  add `desktop/sessions.py` — a DB-style JSON store, one file per session in
  `%LOCALAPPDATA%/<AppName>/sessions/`, mirroring how Hermes keeps per-conversation
  history. Expose REST (`/api/sessions` list, `/api/sessions/new`, `/api/sessions/<id>`
  GET+DELETE, `/api/sessions/current`) and have `/api/chat` accept `session_id`,
  persisting the user turn + AI turn. UI: the user's exact placement is a **Sessions
  panel in the SIDEBAR, between the Chat button and the RAG PDFs button** (i.e. "below
  the chat, above the rag pdf button"). It shows a scrollable session list (title +
  click-to-load), a **＋** for new chat, and a per-row 🗑 to delete (with confirm).
  Init loads the current session's messages. Keep it dependency-free (stdlib json/uuid).
  Full pattern in `references/pywebview_desktop_app.md`.
- **`web_search` tool (DuckDuckGo) is the agent's web-search capability — it was
  BROKEN and looked like "the app can't understand me"**: the old GET to
  `html.duckduckgo.com/html/?q=` is walled by DDG (returns 0 results). The working fix
  is a POST form with ONLY `--data-urlencode q=` to the same endpoint; adding extra
  `--data b=`/`--data kl=` fields silently returns EMPTY. Snippet class is
  `result__snippet` (lowercase s). There is NO official DuckDuckGo MCP server — when the
  user says "add duckduckgo mcp", use `web_search` directly instead of looping on
  `mcp_add_server`. Full pattern + verify snippet in `references/aether_web_search.md`.
- **THREE v1.2.9 DESKTOP BUGS (silent-failure class — the user reads these as
  "the app can't do basic tasks", so verify the EXACT reported path, not just an import):
  (1) Sessions panel click did nothing (only 🗑 worked) — `selectSession()` rendered into
  `#messages`, which is null when not on the Chat view → silent no-op; fix: call
  `showView('chat')` FIRST. (2) App wouldn't open — a stale/zombie `Aether.exe` held the
  `Global\\AetherSingleInstanceMutex` with a dead port, so every launch bailed; fix: verify
  the other instance is actually serving (`/api/health`) before deferring, else take over;
  ALSO never set `ctypes` `errcheck=None` (must be callable or absent) or the build crashes
  at startup. (3) RAG returned nothing — ChromaDB collection was EMPTY (docling startup
  ingest too slow / per-PDF errors aborted the batch); fix: make `index_pdf_watch_dir()`
  resilient (try/except per PDF, collect errors, continue) AND actually run the ingest as a
  background task so the collection populates. Verify with `rag.get_collection().count()>0`.
  Full fixes + the exact mutex code in `references/aether_v1.2.9_fixes.md`.
- **v1.3.0 SESSIONS PANEL REDESIGN (the user's exact "find the session I need" + customization demand)**: a bare title-only list reads blank to the user — they want to SEE what each chat is about and customize it. Implement:
  * **Title + preview**: `_list_sessions()` returns `preview` = first `user` message (Hermes-style, first line of first prompt) + `chars` (total stored chars) for the context meter. UI renders `s-title` + `s-preview` (CSS ellipsis) per row.
  * **3-dot menu on hover**: a `⋯` button per row toggles a small menu with **Pin** (PATCH `pinned:true` → sort pinned-first), **Rename** (`prompt()` → PATCH `title`), **Delete**. Close other menus on open. Pin sort key: `out.sort(key=lambda s: (not s["pinned"], -mtime))` — see the sort-key bug below.
  * **Per-session CONTEXT CIRCLE**: a `conic-gradient` circle showing `round(chars/120000*100)%` of the model's `MAX_PROMPT_CHARS` (120k), with `title="X% used — Y% left"` tooltip. Pure CSS, no lib.
  * **Add-file (📎) in composer, BOTH Normal + RAG**: `POST /api/sessions/{id}/files` stores the path in `session.files`; `api_chat` reads each attached file, prepends its text (cap 8000 chars) to the system prompt for BOTH modes. Verified: model answered from an attached `.txt`. UI shows attached files as chips + `renderAttached()`.
  * **New endpoints**: `PATCH /api/sessions/{id}` (body `{title?, pinned?}`) and `POST /api/sessions/{id}/files` (`{path}`; `{"ok":False}` if file missing). All behind the existing session store.
  * UX detail: clicking a session row must `showView('chat')` BEFORE rendering messages (the v1.2.9 no-op bug) — and the 3-dot `onclick` must `event.stopPropagation()` so it doesn't also trigger row-select.
  * Full pattern + endpoint shapes in `references/aether_v1.3.0_sessions.md`.
- **PYTHON SORT-KEY PRECEDENCE FOOTGUN (500'd `/api/sessions` this session)**: `out.sort(key=lambda s: (not s["pinned"], -SESSIONS_DIR / f"{s['id']}.json".stat().st_mtime))` unary-minuses the **Path** (`SESSIONS_DIR`), not `.stat().st_mtime` → `TypeError: bad operand type for unary -: 'WindowsPath'`. FIX: compute mtime in a helper and negate THAT: `def _mtime(s): ... return (SESSIONS_DIR / f"{s['id']}.json").stat().st_mtime ... ; out.sort(key=lambda s: (not s["pinned"], -_mtime(s)))`. Always wrap `stat()` in try/except (return 0) so a missing file can't 500 the list.
- **Desktop app: full Hermes-One-style SIDEBAR (user's benchmark — expanded this session)** —
  the user grades the desktop app against the **Hermes One** app daily. Expected nav:
  logo + a left sidebar with **Chats** (Normal|RAG toggle, + New chat, session list),
  **RAG PDFs** (shows the drop-in folder PATH, list/add/remove/rebuild, "Sync folder" to
  ingest pasted PDFs — so the user can cut/paste all PDFs into the folder instead of
  adding one-by-one), **Skills** (list EVERY skill, toggle EACH on/off individually,
  edit its SKILL.md, delete), **Tools** (list every built-in tool, toggle EACH on/off
  individually — NOT all-or-nothing), **MCP** (list configured servers, toggle each,
  add/remove), **Memory** (view/edit/delete durable facts), **Persona** (edit SOUL.md +
  USER.md), **Providers** (switch OpenRouter/OpenAI/Ollama + paste own key + model), and
  **Telegram** (paste bot token, set normal/rag mode, start/stop gateway). The user is
  explicit: per-ITEM toggles, like Hermes — not one "tools on/off" switch. Keep ALL of
  this in the UI; do NOT push the user to edit YAML. Full recipe in
  `references/pywebview_desktop_app.md` (and the native-window-preferred packaging rule
  in `windows-desktop-app-packaging`).
- **DESKTOP CHAT ROUTE MUST CALL run_agent() (not provider.chat directly)** — the #1
  reason "the app's agent can't use tools" while the CLI works: the `/api/chat` SSE
  handler calls `provider.chat(messages, stream=True)` directly, bypassing the agent
  loop, so tools/skills/MCP never fire inside the app. Route it through the SAME
  `agent.run_agent(message, mode=..., rag_context=..., on_token=cb)` the CLI uses, then
  stream the assembled answer word-by-word. Verified this session: after the fix the
  app's `/api/chat` built `cal_project/calculator.py` via terminal+write_file — exactly
  like the CLI. (See `references/aether_agent_app.md` for the loop + test.)
- **VERIFY THE FROZEN EXE THROUGH THE REAL BUNDLE, not the MSYS shim**: the
  agent terminal's `python` is the uv shim and its subprocess-pipe behavior
  differs from the frozen `Aether.exe`. A fix proven under the shim can still
  fail in the exe — and vice-versa. Add an `AETHER_HEADLESS=1` guard to
  `main()` (serve, skip WebView2) and launch `./Aether.exe` backgrounded, then
  `curl /api/health` + the route under test. This is the only authoritative way
  to confirm an MCP/startup fix. Full patterns (headless guard, MCP Windows-pipe
  Errno-22 fix, startup-NameError pitfall, gh large-asset upload) in
  `references/aether_frozen_exe.md`.
- **STARTUP CRASH MASQUERADES AS "backend won't start"**: if the app shows
  "could not start its backend server / API did not become ready in time" while
  the port is free, run `tasklist /v | findstr Aether` — `Unhandled exception in
  script` means the app died BEFORE `uvicorn.run` (e.g. a `NameError` from an
  import-order regression). Fix: `import threading as _threading` at the TOP of
  `main()`, start the server thread FIRST, offload heavy RAG ingest to a
  background thread, write `%LOCALAPPDATA%/Aether/aether_startup.log`. Never put
  a misleading antivirus hint in the fail box (this user has no AV).
- **FROZEN-EXE `isatty` CRASH (the real "backend won't start" cause this session)**:
  In a PyInstaller-frozen exe, `sys.stdout` AND `sys.stderr` are `None`. Uvicorn's
  default log formatter (`uvicorn.logging.DefaultFormatter`) calls
  `self.stream.isatty()` → `AttributeError: 'NoneType' object has no attribute
  'isatty'` → `ValueError: Unable to configure formatter 'default'` → `uvicorn.run`
  raises → server never binds → the 45s probe times out → "API did not become ready
  in time". This was the actual root cause behind BOTH the v1.2.x launch failures
  AND the earlier "could not start backend" errors (the NameError was a second,
  separate regression on top). FIX (apply at the very TOP of `main()`, before
  `uvicorn.run` is ever reached): redirect the streams to a real file:
  ```python
  try:
      _logdir = Path(os.environ.get("LOCALAPPDATA", "")) / "Aether"
      _logdir.mkdir(parents=True, exist_ok=True)
      _logfile = open(_logdir / "aether_stdout.log", "a", encoding="utf-8", buffering=1)
      if sys.stdout is None: sys.stdout = _logfile
      if sys.stderr is None: sys.stderr = _logfile
  except Exception:
      pass
  ```
  After this patch the exe starts in ~1-3s. Verify with `AETHER_HEADLESS=1` launch
  + `curl /api/health` (see `references/aether_frozen_exe.md`).
- **PROCESS-HYGIENE / HOST-HERMES CAUTION (after a reboot scare this session)**:
  When TESTING the desktop app, ALWAYS kill the background `Aether.exe`/`uvicorn`/
  `npx` test servers you spawned (use `notify_on_complete` or an explicit
  `process(action='kill')`) before ending the turn. Leftover procs on this 16GB
  machine caused memory/thermal pressure that triggered a reboot. CRITICAL: NEVER
  blanket-kill `node.exe`/`python.exe` (e.g. `taskkill /F /IM node.exe`) — those are
  the USER'S HOST HERMES AGENT's own MCP servers (their ParentProcessId is a host
  Hermes python). Killing them disrupts the user's running agent (they auto-recover,
  but it's a self-inflicted outage). Only kill PIDs you PROVE are Aether test spawns
  (command line contains `Aether`/`uvicorn`/`make_installer`). Inspect first:
  `powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \\\"Name LIKE
  '%Aether%'\\\" | Select ProcessId,CommandLine"`. Full guardrails in
  `references/process_hygiene.md`.
- **PUBLISH LARGE ASSETS IN TWO `gh` STEPS**: `gh release create ...` with the asset
 attached TIMES OUT on uploads above ~100MB (confirmed at 116MB, 176MB AND 181MB this
 session). Create the release with NO asset first, then `gh release upload vX.Y.Z
 dist/<asset> --clobber` (the upload step has a longer effective timeout and
 completes). Always verify the release is NOT a draft afterward
 (`gh release view vX.Y.Z --json isDraft`) and clean up any accidental duplicate
 drafts before re-publishing. Update `project_rag/server.py`'s download redirect to
 the new tag in the same cycle.
 **STALL FALLBACK (this session, 176MB zip stalled 3× at the same point on the user's
 link)**: if `gh release upload` repeatedly stalls (process stays alive 10+ min, draft
 never gets the asset), STOP looping. Either (a) `gh release delete vX.Y.Z -y` then
 recreate with `--notes-file` and retry once, or (b) publish the release NOTES-ONLY
 (no asset) and leave `dist/Aether-X.Y.Z-portable.zip` locally for the user to drag
 into the GitHub release page manually when their connection is stronger. The installed
 exe on the user's machine is already the new version regardless — the GitHub asset is
 only a distribution mirror, not a blocker. Don't burn the turn retrying an upload that
 the network won't complete.

 - **TEST THE APP THROUGH ITS OWN API (don't trust the window, don't kill processes)**:
  to verify the desktop app end-to-end from a headless env, start the backend on a
  FRESH PORT (not the default — avoids clobbering a port the user may have open) and
  drive `/api/chat` + the other routes with `python -c \"urllib.request...\"`:
  ```python
  import desktop_app as d, uvicorn, threading, time, json
  import urllib.request as ureq
  threading.Thread(target=lambda: uvicorn.run(d.app, host='127.0.0.1', port=8744, log_level='warning'), daemon=True).start()
  time.sleep(5)
  req = ureq.Request('http://127.0.0.1:8744/api/chat',
                     data=json.dumps({'mode':'normal','message':CALC_PROMPT}).encode(),
                     headers={'Content-Type':'application/json'})
  for line in ureq.urlopen(req, timeout=180).read().decode().split('\\n\\n'):
      if line.startswith('data: '):
          j = json.loads(line[6:]);  # accumulate j['token']
  ```
  Read the written file / `os.walk(cal_project)` afterward to assert the side effect.
  NEVER run `taskkill`/destructive kill on the user's running app without explicit
  consent — a separate port sidesteps the conflict entirely. Also: `config` key
  `"model"` uses `"default"` (not `"default_model"`) — confirm key names vs DEFAULT_CONFIG.

## References
- `references/fastapi_sse_server.md` — server.py skeleton (queue, SSE, ngrok lifespan, Postgres, cache, `_clean_query`).
- `references/pywebview_desktop_app.md` — desktop_app.py + api_server.py (Chat/Shelf/Settings, masked key). Now also: logo PNG/ICO build + wiring + **modern pywebview `icon=` DOES work** (window/taskbar mark), the full Hermes-style **sidebar** (RAG PDFs panel, Provider key paste, Capability toggles honored in run_agent, Gateway start/stop), the desktop-chat-route-must-call-run_agent pitfall, and session management.
- `references/ngrok_free_tier.md` — authtoken vs API key, static-domain limit, URL stability.
- `references/openrouter_cloud_deploy.md` — OpenRouter conversion of the website (drop Ollama, SSE via OpenRouter), `openrouter/free` free-check quirk, self-contained cloud server + bundle assembly (Render/HF free), and the SSE `curl` verification hang.
- `references/autostart_windows.md` — make the RAG site + tunnel auto-start on logon (Startup Agent_OS.cmd, idempotent, reboot-survival).
- `references/aether_v1.2.9_fixes.md` — the three v1.2.9 silent-failure bugs (sessions-click no-op, stale-mutex app-won't-open, empty-ChromaDB RAG) + exact mutex/errcheck fix + resilient ingest.
- `references/aether_v1.3.0_sessions.md` — v1.3.0 Sessions panel redesign: title+preview list, 3-dot pin/rename menu, per-session context-circle %, add-file (📎) injection for Normal+RAG, new PATCH/POST-files endpoints, and the sort-key unary-minus-on-Path 500 bug.
- `references/hybrid_retrieval.md` — hybrid (dense+BM25+RRF+CrossEncoder rerank) pattern + router/page-path/RBAC/fit_context + eval_rag.py + the 2 plan bugs (docling page path, reranker model ID) + the reranker `reverse=True` dict-crash pitfall + the incremental upload-to-live-collection feature pattern.
- `references/aether_agent_app.md` — distributable Hermes-class agent app (Normal|RAG): the DEAD-TOOL-LOOP pitfall (`tools=` must be passed to the model) + fix pattern, the API-KEY-LEAK pitfall (never read a sibling app's `.env`/hardcode username) + fix, the calculator verification test, AND pitfalls #3–#6: OpenRouter `{"type":"function",...}` wrapper requirement, `KeyError:'name'` from wrapped-schema filtering, "app can't modify its own config" = missing self-config tools (expose `mcp_add_server` etc. + tell the model it can self-manage), and JSON-string tool-arg coercion in `call_tool`.
- `references/aether_frozen_exe.md` — frozen-exe verification via `AETHER_HEADLESS` guard, the MCP stdio Windows-pipe Errno-22 fix (`bufsize=0` binary + `select` timeout), the **frozen-exe `isatty`/`sys.stdout` crash** (the real "backend won't start" root cause) + fix, the startup-NameError "backend won't start" pitfall, and the two-step `gh` 181MB installer upload.
- `references/aether_settings_branding.md` — rename "Hermes One"/"Hermes Agent" -> "Aether" (exact files + the nav-id stays `hermesone` rule), the Settings-UI-calls-missing-backend class bug (`setAppearance` JS + `/api/appearance` + `/api/backup/export|import` wiring + verification grep), the version-bump checklist, and the Inno-Setup-absent portable-zip publish path (draft-duplicate cleanup).
- `references/aether_web_search.md` — `web_search` tool (DuckDuckGo) pitfall: the GET `?q=` endpoint is walled (0 results); the fix is a POST form with ONLY `--data-urlencode q=`; extra `--data b=`/`kl=` fields break it; no official DuckDuckGo MCP exists (use `web_search`); verify snippet.
- `references/aether_execution_animation.md` — SSE execution-step timeline (🧠 thinking → 🔧 tool_start(args) → tool_end(result) → ✍️ answer): backend `step` events in `api_chat`, frontend `.steps` render + CSS, AND the two-layer context compaction (preserve_last_n + 32KB Snip cap) from the Claude Code leak — fixes the "9000 files" blow-up. This is the user's explicit "show me the agent working" + "fuse the PDF + Hermes insights" demand.
- `references/process_hygiene.md` — kill-your-own-test-servers rule, NEVER blanket-kill `node.exe`/`python.exe` (host Hermes owns them), identify-before-kill via `Get-CimInstance`, and the reboot-diagnosis symptom→cause map.
- `references/azure_container_apps_deployment.md` — Azure Container Apps deployment via GitHub Actions OIDC: portal steps (Resource Group, App Registration, Federated Credential, Contributor role), multi-stage Dockerfile (CPU-only torch), pinned requirements (docling 1.20.0, rich<14, chromadb 0.6.3), server.py changes (healthz, graceful shutdown, CHROMA_DB_DIR), GitHub Actions workflows (build-push, deploy-azure), cost optimization (min-replicas=0, scale-to-zero), and frontend integration.
- `templates/interactive_bg.html` — drop-in `<canvas>` particle field + cursor-glow + magnetic-button snippet (chaingpt-style living background). Copy into the web UI and desktop UI.
- **Cache pitfall** (FastAPI `FileResponse` serving `index.html`): ALWAYS set
  `Cache-Control: no-store` on the `/` route or browsers show the OLD UI after edits.
  See the "Critical techniques & pitfalls" list (FastAPI `FileResponse` caching).

## Overlap note
`docling-hybrid-rag` covers the docling ingestion/chunking pipeline (the RAG core). This
skill covers productization (deploy/desktop/UI/privacy). They are complementary; the
curator may link them.