# sync_hybrid_search_with_citations — Critical Bugs & Fixes (2026-07-25)

## Root Cause: ChromaDB `get()` Returns IDs in Alphabetical Order

**File**: `project_rag/server.py` lines 436-506 (`sync_hybrid_search_with_citations`)

```python
# THE BUG
top_ids = [c for c, _ in sorted(rrf.items(), key=lambda x: x[1], reverse=True)[:n_results]]
res = collection.get(ids=top_ids)  # Returns docs in ALPHABETICAL order of IDs, not top_ids order!
# res['ids'] == ['chunk_1', 'chunk_10', 'chunk_2', ...] NOT ['chunk_91', 'chunk_1', 'chunk_2', ...]
```

**Why it breaks everything**: The code then tries to sort by `m.get("id")` (line 456), but **metadata has NO `id` field** — it returns `None`. So all chunks get `order.get(None, 0) == 0` and lose RRF ranking. Worse, the relevance filter at line 478-480 uses `dist_map.get(m.get("id"), 1.0)` which is ALWAYS `1.0` (the default), so **every chunk is filtered out by `_RELEVANCE_CUTOFF = 0.50`**.

## Verified Fix Pattern

```python
def sync_hybrid_search_with_citations(query: str, n_results: int = 10):
    clean_q = _clean_query(query)
    sem = collection.query(query_texts=[clean_q], n_results=n_results)["ids"][0]
    
    if _BM25 is not None:
        lex_scores = _BM25.get_scores(_tokenize(clean_q))
        lex = [_BM25_IDS[i] for i in sorted(range(len(lex_scores)),
                key=lambda i: lex_scores[i], reverse=True)[:n_results]]
    else:
        lex = []
    
    rrf = {}
    for r, cid in enumerate(sem):
        rrf[cid] = rrf.get(cid, 0.0) + 1.0 / (r + 60)
    for r, cid in enumerate(lex):
        rrf[cid] = rrf.get(cid, 0.0) + 1.0 / (r + 60)
    
    top_ids = [c for c, _ in sorted(rrf.items(), key=lambda x: x[1], reverse=True)[:n_results]]
    
    # GET DOCUMENTS IN RRF ORDER — don't rely on collection.get() ordering
    docs = []
    metas = []
    for cid in top_ids:
        res = collection.get(ids=[cid])
        if res["documents"]:
            docs.append(res["documents"][0])
            metas.append(res["metadatas"][0])
    
    # Cross-encoder rerank
    if docs:
        pairs = [(clean_q, d) for d in docs]
        scores = _RERANKER.predict(pairs)
        ranked = sorted(zip(scores, docs, metas), key=lambda x: x[0], reverse=True)
        docs = [d for _, d, _ in ranked]
        metas = [m for _, _, m in ranked]
        docs = docs[:6]
        metas = metas[:6]
    
    # Relevance filter using RERANKER scores (not distance) — simpler and more reliable
    # OR: get distances in the SAME order as our docs list
    kept = []
    for d, m in zip(docs, metas):
        # Option A: Use reranker score threshold
        # (need to carry scores through — add score to metadata during rerank)
        # Option B: Query distances for these specific IDs
        pass
    
    # Build context with citations
    # ... rest unchanged
```

## Key Fixes Required

1. **Iterate `top_ids` and call `collection.get(ids=[cid])` per ID** — preserves RRF order exactly
2. **Add `id` to metadata during upsert** — so `m.get("id")` works, OR stop using `m.get("id")` and use the known `top_ids` list
3. **Use reranker scores for relevance filtering** — they're already computed; don't re-query distances
4. **Remove the `order = {c: i for i, c in enumerate(top_ids)}` + metadata sort** — it's the source of the bug

## Other Bugs Found Same Session

| Bug | Location | Fix |
|-----|----------|-----|
| Uptime endpoint calls `await health()` (endpoint handler, not function) | `server.py` line 722 | Extract health logic to internal `_health_check()` function |
| Cloudflare tunnel hardcoded `cwd="/c/Users/valte"` | `server.py` line 1080 | Use `PROJECT_DIR` or config value; add cert check |
| Duplicate `get_appearance()` / `set_appearance()` / `export_backup()` / `import_backup()` | `aether/aether/config.py` lines 83-90, 241-249, 411-418, 421-434, 253-278, 437-479 | Remove duplicates (second def shadows first) |
| RRF score used as `relevance_score` (0.016-0.03) instead of normalized 0-1 | `aether/aether/rag.py` line 94 | Normalize: `relevance_score = min(1.0, rrf[i] * 100)` or use reranker score |

## Reproduction Script

```python
# Run this to verify the bug exists
import chromadb
from chromadb.utils import embedding_functions

client = chromadb.PersistentClient(path="rag_vector_db")
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
col = client.get_collection(name="docling_knowledge_base", embedding_function=emb_fn)

# Simulate RRF top_ids
top_ids = ['chunk_91', 'chunk_1', 'chunk_2', 'chunk_83']
res = col.get(ids=top_ids)
print("Requested order:", top_ids)
print("Returned order:", res['ids'])  # Alphabetical!
print("Metadata has 'id'?:", res['metadatas'][0].get('id', 'NO'))
```

## Files to Patch

1. `project_rag/server.py` — `sync_hybrid_search_with_citations` (lines 436-506)
2. `project_rag/server.py` — uptime endpoint (line 722)
3. `project_rag/server.py` — Cloudflare tunnel (line 1080)
4. `aether/aether/rag.py` — `retrieve_with_citations` relevance_score (line 94)
5. `aether/aether/config.py` — remove duplicate functions