---
name: rag-with-citations
description: Enhanced RAG pipeline with hybrid search (dense + BM25), cross-encoder reranking, relevance filtering, and structured citation metadata for UI display.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
category: mlops
tags: [rag, hybrid-search, bm25, cross-encoder, reranking, citations, chromadb, openrouter]
---

# RAG with Citations Skill

## Overview
Enhanced RAG pipeline that adds structured citation metadata (source file, page, headings, relevance score) to every answer, enabling UIs to render "📚 Sources" footers with clickable references and confidence indicators.

## Core Pipeline

### 1. Hybrid Retrieval (Dense + Lexical)
```python
def sync_hybrid_search(query: str, n_results: int = 10):
    clean_q = _clean_query(query)
    # Dense (Chroma embedding)
    sem = collection.query(query_texts=[clean_q], n_results=n_results)["ids"][0]
    # Lexical (BM25)
    lex_scores = _BM25.get_scores(_tokenize(clean_q))
    lex = [_BM25_IDS[i] for i in sorted(range(len(lex_scores)), key=lambda i: lex_scores[i], reverse=True)[:n_results]]
    # Reciprocal Rank Fusion
    rrf = {}
    for r, cid in enumerate(sem):
        rrf[cid] = rrf.get(cid, 0.0) + 1.0 / (r + 60)
    for r, cid in enumerate(lex):
        rrf[cid] = rrf.get(cid, 0.0) + 1.0 / (r + 60)
    top_ids = [c for c, _ in sorted(rrf.items(), key=lambda x: x[1], reverse=True)[:n_results]]
    return top_ids
```

### 2. Cross-Encoder Reranking
```python
_RERANKER = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
pairs = [(clean_q, d) for d in docs]
scores = _RERANKER.predict(pairs)
ranked = sorted(zip(scores, docs, metas), key=lambda x: x[0], reverse=True)
```

### 3. Relevance Guard (Semantic Distance Threshold)
```python
_RELEVANCE_CUTOFF = 0.50  # cosine distance > 0.5 = unrelated
dist_res = collection.query(query_texts=[clean_q], n_results=len(docs))
dist_map = {cid: dist for cid, dist in zip(dist_res["ids"][0], dist_res["distances"][0])}
kept = [(d, m) for d, m in zip(docs, metas) if dist_map.get(m.get("id"), 1.0) <= _RELEVANCE_CUTOFF]
```

### 4. Citation-Enriched Output
```python
def sync_hybrid_search_with_citations(query: str, n_results: int = 10):
    # ... retrieval + rerank + relevance filter ...
    sources = []
    for doc, m in zip(docs, metas):
        sources.append({
            "doc_id": m.get("id", "?"),
            "source_file": m.get("source", "unknown"),
            "page": m.get("page"),
            "headings": m.get("headings", ""),
            "chunk_id": m.get("chunk_id"),
            "relevance_score": round(1.0 - dist_map.get(m.get("id"), 0.5), 3),
        })
    return retrieved_context, sources, had_context
```

### 5. Answer Cache with Citations
```python
_ANSWER_CACHE: dict[str, tuple[str, list, float]] = {}  # (answer, citations, timestamp)

def _cache_get(q):  # returns (answer, citations) or (None, None)
def _cache_put(q, ans, citations):
```

### 6. Streaming Response with Citations
```python
# During streaming:
yield f"data: {json.dumps({'token': token})}\n\n"
# At end:
yield f"data: {json.dumps({'done': True, 'citations': sources})}\n\n"
```

## UI Integration (Website + Desktop App)
- **Website**: `cites` div rendered from `j.citations` array with relevance %
- **Desktop App**: `addMsg()` handles both old string format and new object format:
```javascript
const src = x.source_file || x;
const page = x.page ? ` p.${x.page}` : '';
const head = x.headings ? ` — ${x.headings}` : '';
const rel = x.relevance_score ? ` (${Math.round(x.relevance_score*100)}%)` : '';
```

## Key Parameters
| Param | Default | Purpose |
|-------|---------|---------|
| `_RELEVANCE_CUTOFF` | 0.50 | Semantic distance above which chunks are discarded |
| `_MAX_CONTEXT_CHARS` | 26000 | Keeps 9B model in 32K window |
| `n_results` | 10 | Initial candidates before rerank |
| Cross-encoder | ms-marco-MiniLM-L-6-v2 | Fast, accurate reranker |

## Files Modified in This Repo
- `project_rag/server.py` — `sync_hybrid_search_with_citations`, `generate_rag_stream` with citation yield
- `project_rag/web_ui/index.html` — citation rendering in chat
- `aether/aether/rag.py` — `retrieve_with_citations` returns structured metadata
- `aether/desktop_ui/index.html` — `addMsg()` handles object-format citations

## References
- `references/rag-pipeline-architecture.md` — full pipeline diagram and parameter table
- `references/session-2026-07-23-rag-citations.md` — session log: implemented structured citations (source_file, page, headings, relevance_score) in both website and desktop app; fixed answer cache to store/return citations; added /api/app/update-check and /api/uptime endpoints

## Session Learnings (2026-07-23)
- **Confirmed**: Hybrid search (Chroma dense + BM25) + CrossEncoder rerank + relevance cutoff (0.5 cosine distance) produces high-quality grounded answers
- **Confirmed**: Structured citations (source_file, page, headings, relevance_score) enable rich UI rendering in both website and desktop app
- **Confirmed**: Answer cache must store citations alongside answer text; cache hits now return citations for immediate UI display
- **Confirmed**: New endpoints `/api/app/update-check` and `/api/uptime` registered but not visible until Python bytecode cache cleared and server restarted
- **Pitfall**: FastAPI route decorators must be applied AFTER `app = FastAPI(...)` is created; adding them before `app` definition causes NameError

## Verification
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "what is RAG"}'
# Final line should include: {"done": true, "citations": [...]}
```