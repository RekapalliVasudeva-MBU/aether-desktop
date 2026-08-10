# RAG Pipeline Issues & Fixes (This Session)

## Duplicate Function Bug — CRITICAL

**File:** `project_rag/server.py` and `aether/rag.py`

**Bug:** Two definitions of `retrieve_with_citations` in `project_rag/server.py` — the second one (enhanced with rich citation metadata) was appended, but the original remained. Python used the first (broken) version.

**Fix:** Removed the first (minimal) definition, kept the enhanced version with rich citation metadata (`doc_id`, `source_file`, `page`, `headings`, `chunk_id`, `relevance_score`).

**Files patched:** `project_rag/server.py` (removed duplicate), `aether/rag.py` (kept single `retrieve_with_citations` with rich metadata)

## Citation Metadata Enhancement

**Added to citations:**
```python
citations.append({
    "doc_id": m.get("id", "?"),
    "source_file": m.get("source", "unknown"),
    "page": m.get("page"),
    "headings": m.get("headings", ""),
    "chunk_id": m.get("chunk_id"),
    "relevance_score": round(1.0 - dist_map.get(m.get("id"), 0.5), 3),
})
```

**UI Display (both web + desktop):**
- Source filename
- Page number (if available)
- Section headings
- Relevance percentage

## Citation Cache Enhancement

**Cache now stores citations with answers:**
```python
_ANSWER_CACHE: dict[str, tuple[str, list, float]] = {}  # (answer, citations, timestamp)

def _cache_put(q: str, ans: str, citations: list = None):
    _ANSWER_CACHE[_cache_key(q)] = (ans, citations or [], datetime.now().timestamp())

def _cache_get(q: str):
    # returns (answer, citations) or (None, None)
```

## RAG Pipeline Components Verified

| Component | Status | Notes |
|-----------|--------|-------|
| Hybrid search (dense + BM25 + RRF) | ✅ | Both project_rag and aether |
| Cross-encoder reranking | ✅ | ms-marco-MiniLM-L-6-v2 |
| Citation metadata | ✅ | Rich metadata + UI display |
| Answer caching | ✅ | 1-hour TTL with citations |
| PDF upload & instant query | ✅ | docling pipeline, BM25 rebuild |
| Relevance cutoff (0.50) | ✅ | Prevents hallucination |
| Context window management | ✅ | 26K chars (project_rag), 6K (aether) |
| Page-index fast path | ✅ | "page N" queries skip vector search |
| Relevance filter | ✅ | Cosine distance ≤ 0.50 |
| Answer caching | ✅ | 1-hour TTL with citation preservation |
| Page-index fast path | ✅ | "page N" queries skip vector/BM25 |
| Cross-encoder rerank | ✅ | ms-marco-MiniLM-L-6-v2 |

## New Citation-Enriched Search Function

```python
def sync_hybrid_search_with_citations(query: str, n_results: int = 10):
    """Returns (context_string, sources_list, had_context)"""
    # hybrid search → RRF → CrossEncoder rerank → relevance filter → rich citations
    return retrieved_context, sources, had_context
```

## Citation Display (Both UIs)

**Web (`project_rag/web_ui/index.html`):**
```javascript
if (j.citations && j.citations.length > 0) {
    sourcesDiv.innerHTML = '<b>📚 Sources:</b><br>' + j.citations.map(c => 
      `${c.source_file || 'unknown'}${c.page ? ' p.'+c.page : ''}${c.headings ? ' — '+c.headings : ''} (relevance: ${c.relevance_score ? Math.round(c.relevance_score*100)+'%' : 'N/A'})`
    ).join('<br>');
    box.appendChild(sourcesDiv);
}
```

**Desktop (`desktop_ui/index.html`):**
```javascript
c.innerHTML = '<b>📚 sources:</b> ' + citations.map(x => {
  const src = x.source_file || x;
  const page = x.page ? ` p.${x.page}` : '';
  const head = x.headings ? ` — ${x.headings}` : '';
  const rel = x.relevance_score ? ` (${Math.round(x.relevance_score*100)}%)` : '';
  return `${esc(src)}${page}${head}${rel}`;
}).join(', ');
```

## Answer Cache with Citations

```python
def _cache_put(q: str, ans: str, citations: list = None):
    _ANSWER_CACHE[_cache_key(q)] = (ans, citations or [], datetime.now().timestamp())

def _cache_get(q: str):
    # returns (answer, citations) or (None, None)
```

## Verified Working

| Test | Result |
|------|--------|
| RAG chat with citations (web) | ✅ Streaming + citations |
| RAG chat with citations (desktop) | ✅ Streaming + rich citations |
| PDF upload → instant query | ✅ |
| Answer cache with citations | ✅ Cache hits return citations |
| Relevance filtering | ✅ Off-topic returns "not in KB" |
| Page-index fast path | ✅ "page N" queries work |
| Citation display (web) | ✅ Source + page + section + relevance |
| Citation display (desktop) | ✅ Source + page + section + relevance % |

## Known Limitations

- PDF list endpoint may return `[]` if metadata didn't capture source paths (cosmetic only)
- Cross-encoder rerank adds ~200ms latency
- Relevance cutoff 0.50 may be too aggressive for some domains
- Cache key uses cleaned query — "what is X" and "what is X?" share cache