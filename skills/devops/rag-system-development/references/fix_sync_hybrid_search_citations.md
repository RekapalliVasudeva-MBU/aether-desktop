# Fix: sync_hybrid_search_with_citations Bug (2026-07-25)

## Problem
The `sync_hybrid_search_with_citations` function in `project_rag/server.py` had **three critical bugs** that caused the RAG chat to return "I don't have information about that in my knowledge base" even when 572 relevant chunks existed in ChromaDB.

## Root Cause Analysis

### Bug 1: ChromaDB `get()` Returns Alphabetical Order
```python
# WRONG - collection.get() ignores request order, returns alphabetical
top_ids = ['chunk_91', 'chunk_1', 'chunk_2', ...]  # RRF ranked order
res = collection.get(ids=top_ids)  # Returns ['chunk_1', 'chunk_10', 'chunk_100', ...] ALPHABETICAL!
```

### Bug 2: Metadata Has NO `id` Field
```python
# WRONG - metadata never contains "id" key
dist_map.get(m.get("id"), 1.0)  # Always returns 1.0 (default)
# Result: ALL chunks get distance 1.0 > _RELEVANCE_CUTOFF (0.50) → ALL FILTERED OUT
```

### Bug 3: Reranker Scores Discarded
Cross-encoder reranking happened but its scores were never used for relevance filtering — the code fell back to distance-based filtering which was broken by Bug 2.

## The Fix

## Solution Applied

### 1. Preserve RRF Order: Fetch IDs Individually
```python
# CORRECT - fetch each ID individually to preserve RRF ranking
docs = []
metas = []
for cid in top_ids:
    res = collection.get(ids=[cid])
    if res["documents"]:
        docs.append(res["documents"][0])
        metas.append(res["metadatas"][0])
```

### 2. Use Reranker Scores for Relevance (Not Distance)
```python
# Store reranker score in metadata
for i, (score, _, m) in enumerate(ranked):
    if i < len(metas):
        metas[i] = dict(m)
        metas[i]["_rerank_score"] = float(score)

# Filter by reranker score (typically 0-10 range)
kept = [(d, m) for d, m in zip(docs, metas) if m.get("_rerank_score", 0) > 2.0]
```

### 3. Normalize Reranker Score for Display
```python
rerank_score = m.get("_rerank_score", 0)
relevance = min(1.0, max(0.0, rerank_score / 10.0))  # normalize to 0-1
sources.append({"relevance_score": round(relevance, 3), ...})
```

## Verification
After fix, test query "What is RAG?" should:
1. Return top 6 chunks with reranker scores > 2.0
2. Build context from those chunks
3. Call OpenRouter with context
4. Return grounded answer with citations showing relevance ~0.3-0.8

## File Location
`project_rag/server.py` — function `sync_hybrid_search_with_citations` (lines ~436-506)

## Related
- `references/docling_api.md` — docling pipeline that built the 572 chunks
- `scripts/verify_rag.py` — (to create) verification script for this fix