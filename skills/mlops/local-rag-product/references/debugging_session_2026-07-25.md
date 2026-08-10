# Debugging Session 2026-07-25 — RAG Website + Desktop App Recovery

## Context
Yesterday's session got stuck: server crashed on startup (empty ChromaDB collection), BM25 index crashed on empty collection, port 8000 held by stale processes, OpenRouter model returning 404.

## Root Causes Found & Fixed

### 1. Empty ChromaDB Collection → Server Crash
**Error**: `chromadb.errors.NotFoundError: Collection [docling_knowledge_base] does not exist`
**Fix**: The collection was deleted when clearing the DB but never recreated. Re-ran `main.py` docling pipeline → **27 PDFs → 572 chunks** indexed.
**Lesson**: Always verify collection exists after `client.delete_collection()` — use `get_or_create_collection()` or re-run ingestion.

### 2. BM25 Index Crash on Empty Collection
**Error**: `ZeroDivisionError: division by zero` in `rank_bm25._initialize()` at server.py:392
**Root Cause**: `_BM25 = BM25Okapi([_tokenize(d) for d in _BM25_DOCS])` when `_BM25_DOCS == []`
**Fix Applied** (server.py lines 389-398):
```python
_all = collection.get()
_BM25_DOCS = _all["documents"]
_BM25_IDS = _all["ids"]

# Handle empty collection gracefully
if _BM25_DOCS and len(_BM25_DOCS) > 0:
    _BM25 = BM25Okapi([_tokenize(d) for d in _BM25_DOCS])
else:
    _BM25 = None
    print("⚠️ ChromaDB collection is empty — BM25 index not built (will use semantic search only)")
```
**Also guarded** `sync_hybrid_search` and `sync_hybrid_search_with_citations` to check `_BM25 is not None` before calling `.get_scores()`.

### 3. Relevance Filter Bug — Missing "id" in Metadata
**Symptom**: Chat returns "I don't have information about that in my knowledge base" despite relevant chunks (distances 0.30–0.45)
**Root Cause**: Line 475 in `sync_hybrid_search_with_citations`:
```python
kept = [(d, m) for d, m in zip(docs, metas) if dist_map.get(m.get("id"), 1.0) <= _RELEVANCE_CUTOFF]
```
Metadata has NO `"id"` field — so `m.get("id")` returns `None` → `dist_map.get(None, 1.0)` = `1.0` → `1.0 > 0.50` → **ALL FILTERED OUT**.

**Fix**: Use the known chunk IDs from RRF step (which are the actual ChromaDB IDs) instead of reading from metadata:
```python
# The IDs are in dist_res["ids"][0] in the same order as docs/metas after rerank
kept = []
for i, (d, m) in enumerate(zip(docs, metas)):
    cid = dist_res["ids"][0][i] if i < len(dist_res["ids"][0]) else None
    if cid and dist_map.get(cid, 1.0) <= _RELEVANCE_CUTOFF:
        kept.append((d, m))
```

### 4. Cloudflare Quick Tunnel — Zero-Auth Fallback
When ngrok tokens failed (revoked/expired), Cloudflare quick tunnel worked with **NO credentials**:
```bash
curl -sL -o cloudflared.exe https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
./cloudflared.exe tunnel --url http://localhost:8000
# Prints: "Your quick Tunnel has been created! Visit it at: https://<random>.trycloudflare.com"
```
**Caveat**: URL is random and changes every restart. For stable URL, need named tunnel + origin cert.

### 5. Named Tunnel Needs Origin Cert
**Error**: `Cannot determine default origin certificate path. No file cert.pem in [~/.cloudflared ~/.cloudflare-warp ~/cloudflare-warp]`
**Fix**: Run `cloudflared tunnel login` (opens browser) to generate `~/.cloudflared/cert.pem`, then `cloudflared tunnel create aether-rag`. Token goes in `server_config.json`.

### 6. OpenRouter Model Update
**Old**: `tencent/hunyuan-a13b-instruct:free` → 404 "model unavailable for free"
**New**: `nvidia/nemotron-3-ultra-550b-a55b:free` → **verified working** via direct API test
**Updated in**: `server_config.json` → `"openrouter_model": "nvidia/nemotron-3-ultra-550b-a55b:free"`

### 7. Port Conflict Resolution
Stale uvicorn processes held port 8000. Pattern:
```bash
netstat -ano | findstr :8000
taskkill /F /PID <pid>
```

## Verification Results
- ✅ Local server: `http://127.0.0.1:8000` — health shows 572 chunks, postgres ON
- ✅ Website UI loads completely (landing, chat, knowledge, download)
- ✅ Semantic search returns relevant results (distances 0.30–0.45)
- ✅ **Chat now returns grounded answers WITH citations** (fixed relevance filter)
- ✅ Quick Cloudflare tunnel running (URL pending capture)
- ✅ Desktop installer exists at `aether/dist/Aether-Setup.exe`
- ✅ Today's RAG News Digest generated: `RAG_News_Digest_2026-07-25.md`

## Open Items
- Capture quick tunnel URL (restart tunnel + catch first 10s of output)
- Set up named Cloudflare tunnel for stable `aether-rag.cfargotunnel.com`
- Add auto-start (Startup folder `Agent_OS.cmd`) for reboot survival
- Consider cloud deploy (Render/HF Spaces) for 24/7 without laptop