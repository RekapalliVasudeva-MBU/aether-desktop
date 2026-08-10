---
name: local-rag-app
description: Build, debug, and operate a local RAG chat web app (local Ollama + docling + ChromaDB + FastAPI SSE + ngrok). Covers the high-value answer-quality recipe for weak/quantized local models (grounding cutoff, chunk-marker stripping, teaching-style prompt with few-shot), plus the recurring UI/ops pitfalls (whole-<script> JS death, SPA caching, ngrok 3-session limit, Windows git-bash PID mismatch).
category: mlops
---

# Local RAG Web App (Ollama + docling + ChromaDB + FastAPI + ngrok)

Use this skill whenever you build, fix, or tune a self-hosted RAG chat site that
answers from a local vector DB using a local/quantized LLM. The single most common
failure mode — and the one this skill exists to prevent — is a RAG that *retrieves*
correctly but *answers* badly: thin one-liners, chunk metadata leaking into output,
model narrating its reasoning, or hallucinating on off-topic questions.

## When to load
- User reports "the chat answers are bad / thin / not explaining / showing chunk names".
- Building a RAG chat endpoint, SSE stream, or desktop wrapper around a local model.
- Debugging why a UI "shows old version" after an update (usually caching or a JS
  syntax error — see Pitfalls).
- Operating ngrok on a free plan or restarting the server on Windows.

## The answer-quality recipe (for weak/quantized local models, e.g. 9B abliterated)
Weak local models follow prompt structure poorly. Get good answers with ALL of:

1. **Retrieve more, then cut by relevance.** Query `n_results=6`. Apply a cosine
   **distance cutoff of 0.50**: drop any chunk with `distance > 0.50`. If nothing
   survives, return the honest fallback line (below) — this is what stops off-topic
   hallucination. See `references/answer_quality.md` for ChromaDB distance calibration.
2. **Strip chunk metadata from the context string.** NEVER send
   `--- Chunk N (Source: ... | Section: ...) ---` to the model. The model echoes it
   into the answer. Strip lines starting with `--- Chunk` before concatenating.
3. **System prompt that teaches, not narrates.** Must include:
   - "Write the final answer directly — no meta-commentary, no 'Looking at the CONTEXT'."
   - "Give a SUBSTANTIVE explanation (at least 3-4 sentences) using the specific
     details, examples, and analogies in the CONTEXT. Do NOT stop at a one-line definition."
   - "Never mention chunk numbers, source labels, or section markers."
   - A **few-shot example** of a good teaching answer (this alone dramatically improves
     weak-model output — see template in `references/answer_quality.md`).
4. **Honest fallback** when no chunk passes the cutoff:
   `"I don't have information about that in my knowledge base."` + "Do NOT use outside
   knowledge."

Verified before/after for "what is rag" with a 9B abliterated model is in
`references/answer_quality.md`.

## Verification (run after any prompt/retrieval change)
Use `scripts/verify_rag.py` against the live endpoint. It asserts:
- `"Chunk"` not in answer (no metadata leak)
- no narration phrases ("Looking at the CONTEXT", "I need to find")
- an off-topic question returns the "not in my knowledge base" line (grounding works)

```bash
python scripts/verify_rag.py http://127.0.0.1:8000
```

## Pitfalls
- **A single JS syntax error kills the ENTIRE `<script>` block.** HTML still renders
  (so text "looks updated") but `checkHealth()` stays stuck on "checking server…" and
  canvas/magnetic animations never run. Cause: often an over-escaped backslash before an
  apostrophe inside a single-quoted string (`'You\\\\'re on the list!'`). Fix: use double
  quotes. Validate JS headlessly: `node -e "const fs=require('fs');const h=fs.readFileSync('web_ui/index.html','utf8');new Function(h.match(/<script>([\s\S]*)<\/script>/)[1]);console.log('VALID')"`.
- **SPA shell caching.** If you update the UI but visitors still see the old page, the
  server is likely sending `ETag`/`Last-Modified` with no `Cache-Control: no-store`. Set
  on the `/` route: `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` +
  `Pragma: no-cache` + `Expires: 0`. (Restart required; the new process must send the
  header. Confirm via `curl -I` / the response headers.)
- **ngrok free plan = max 3 simultaneous agent sessions.** Orphaned `ngrok.exe` from
  earlier CLI tunnels eat slots → new tunnel fails with "limited to 3 simultaneous ngrok
  agent sessions". Kill orphans (keep the one forwarding to your server). See
  `references/ops_windows.md`.
- **Windows git-bash cannot kill Windows-native PIDs.** `kill -9 <pid>` and
  `taskkill //PID <pid> /F` (note the doubled slash) both fail from git-bash because of a
  PID-namespace mismatch. Use `cmd.exe /c "taskkill /PID <pid> /F"`.
- **Don't re-bind ngrok after a server restart.** The existing ngrok tunnel forwards to
  `localhost:8000`; restarting the server serves new code through the SAME public URL. Only
  re-bind if the tunnel itself died.

## Support files
- `references/answer_quality.md` — exact system-prompt template, few-shot example,
  ChromaDB distance calibration table, before/after outputs.
- `references/ops_windows.md` — ngrok orphan cleanup, server restart + health check,
  bash/cmd PID-kill procedure.
- `scripts/verify_rag.py` — live endpoint probe for chunk-leak / narration / grounding.
