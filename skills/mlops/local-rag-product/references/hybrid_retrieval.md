# Hybrid RAG retrieval — dense + BM25 + RRF + CrossEncoder rerank

Condensed, working pattern for the AetherMind RAG (and any docling+ChromaDB RAG).
Two pseudo-code traps from the user's plan were fixed here — see PITFALLS.

## KEEP / DROP guard (prevents bloat)
KEEP: ChromaDB vector + BM25 (`rank_bm25`) + page metadata + rule router + RRF + local
CrossEncoder + offline eval.
DROP: FAISS/bge-m3 swap · LLM router · Whoosh/Tantivy · bge-reranker-v2-m3 · separate
table/OCR stores. No new DB, no model swap, no new service. Only 2 new components:
a BM25 index + a CrossEncoder.

## Ingest metadata (Step 0) — BOTH main.py
```python
# docling >=0.5 stores page in doc_items[].prov, NOT chunk.meta.page_no
page_no = -1
try:
    prov = chunk.meta.doc_items[0].prov
    if prov:
        page_no = prov[0].page_no
except Exception:
    page_no = -1
final_database_chunks.append({
    "text": chunk.text, "source": pdf.name,
    "headings": chunk.meta.headings, "page": page_no,
})
# at metadata write:
metadatas.append({"source": chunk["source"], "headings": headings_str,
                  "page": int(chunk.get("page", -1)), "access": "public"})
```

## Router + BM25 + RRF + rerank (Steps 1-4)
```python
import re
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

_PAGE_RE = re.compile(r"page\s+(\d+)", re.IGNORECASE)
def route_query(q):
    m = _PAGE_RE.search(q)
    return ("page", int(m.group(1))) if m else ("hybrid", None)

def _tokenize(t): return re.findall(r"\w+", t.lower())
_all = collection.get()
_BM25 = BM25Okapi([_tokenize(d) for d in _all["documents"]])
_RERANKER = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")  # LOCAL

def sync_hybrid_search(query, n_results=10):
    clean_q = _clean_query(query)
    sem = collection.query(query_texts=[clean_q], n_results=n_results)["ids"][0]
    lex_scores = _BM25.get_scores(_tokenize(clean_q))
    bm25_ids = collection.get()["ids"]
    lex = [bm25_ids[i] for i in sorted(range(len(lex_scores)),
            key=lambda i: lex_scores[i], reverse=True)[:n_results]]
    rrf = {}
    for r, cid in enumerate(sem): rrf[cid] = rrf.get(cid, 0.0) + 1.0/(r+60)
    for r, cid in enumerate(lex): rrf[cid] = rrf.get(cid, 0.0) + 1.0/(r+60)
    top_ids = [c for c, _ in sorted(rrf.items(), key=lambda x: x[1], reverse=True)[:n_results]]
    res = collection.get(ids=top_ids)
    order = {c: i for i, c in enumerate(top_ids)}
    paired = sorted(zip(res["documents"], res["metadatas"]),
                    key=lambda x: order.get(x[1].get("id"), 0))
    return [d for d, _ in paired], [m for _, m in paired]

# in generate(): route, then either page fast-path or hybrid+RRF+rerank(top6)
docs, metas = sync_hybrid_search(q)
pairs = [(clean_q, d) for d in docs]
scores = _RERANKER.predict(pairs)
ranked = sorted(zip(scores, docs, metas), reverse=True)[:6]
```

## RBAC + fit_context (Step 6)
- RBAC: tag `access:"public"|"premium"` at ingest; filter `if m.get("access","public") in {"public"}`.
- fit_context: cap context ~26K chars (qwythos-9b ~32K); break before appending when over cap.

## Eval layer (Step 5) — eval_rag.py
Golden `EVAL_QUESTIONS = [(question, expected_source_pdf), ...]`. For each: run OLD
(pure `collection.query(n=5)`) and NEW (hybrid top-6). Compute recall@K (did golden
source appear in top-K metadata?), context_recall + faithfulness judged by LOCAL Ollama
(prompt asks judge to reply `context_recall: yes/no` / `faithfulness: yes/no`). Print
OLD vs NEW summary + save `eval_results.json`. Proves the gain before/after a retrieval
change. Note: full eval (20 generations + 20 judgments on 9B local) takes ~8-10 min.

**Caveat — judge metrics are non-deterministic.** `context_recall` and
`faithfulness` are scored by a local 9B judge, so they vary run-to-run (one run
gave OLD ctx_recall 0.80, another 0.60). The *deterministic* signal is
`recall@K` (pure retrieval, no generation). In the run that produced the final
numbers: NEW matched OLD on recall@5/recall@6 (0.80) but beat it on
context_recall (0.60 → 1.00) and faithfulness (0.70 → 0.90). Treat judge rows
as directional, not exact; the consistent finding across runs is NEW ≥ OLD,
never worse. Run the eval in the background (`notify_on_complete=true`) and tail
a log file, since it exceeds the terminal's 60s foreground cap.

## PITFALLS (the two bugs in the user's plan)
1. **docling page path is version-specific.** The plan's `chunk.meta.page_no` does NOT
   exist in docling >=0.5 (chunk `.meta` is `DocMeta` with no page field). The real path
   is `chunk.meta.doc_items[0].prov[0].page_no`. Always wrap in try/except -> -1 fallback.
   `ProvenanceItem` is importable from `docling_core.types.doc` for type hints.
2. **CrossEncoder model ID was wrong.** `sentence-transformers/ms-marco-MiniLM-L-6-v2`
   returns 401/Not Found. Correct local MS-MARCO cross-encoder:
   `cross-encoder/ms-marco-MiniLM-L-6-v2` (verified: scores `[5.65, -11.41]` correctly
   rank a RAG passage above an unrelated one). Pre-download once in background; on Windows
   HF cache warns about symlinks (harmless — set `HF_HUB_DISABLE_SYMLINKS_WARNING=1`).
3. **`rank_bm25` was not installed** in the venv — `pip install "rank_bm25>=0.2.2,<0.3"`.
   `sentence_transformers` was already present.
4. **Reranker init is slow in-process** (~10s to load weights) — build BM25 + reranker
   once at import/startup, not per-query. In a `bottle`/threaded server, build them
   lazily behind a `_ensure_indexes(col)` guard on first request.
5. **RERANKER SORT BUG (expensive, surfaced by uploads).** Do NOT write
   `sorted(zip(scores, docs, metas), reverse=True)`. When two reranker scores TIE,
   Python falls through to comparing `docs` then `metas` — and `metas` are dicts, so it
   raises `'<' not supported between instances of 'dict' and 'dict'`. This only crashes
   once enough chunks exist with tied scores (it stayed latent for months, then fired the
   moment an upload added more chunks). FIX — sort by score ONLY:
   ```python
   ranked = sorted(zip(scores, docs, metas), key=lambda x: x[0], reverse=True)
   docs = [d for _, d, _ in ranked]; metas = [m for _, _, m in ranked]
   ```
   Always reproduce query failures with `--max-time 150` on the SSE endpoint and dump the
   raw `data: {...}` frames — a `{"error": "..."}` frame inside the stream is how this
   surfaced (not an HTTP 500).

## Incremental upload → live collection (feature: chat "📎 add file")
Goal: let a visitor attach a PDF; add it to the SAME ChromaDB as the base PDFs (not wipe),
then answer over the combined corpus. Implemented at `/api/upload` + `main.chunk_single_pdf`
(web) and mirrored in `desktop/api_server.py`.
- **Reuse the existing pipeline** — factor a `chunk_single_pdf(pdf_path, temp_folder)` in
  `main.py` that calls the SAME `build_converter()` + `HybridChunker` (cache the converter/
  chunker module-level so repeated uploads don't reinit docling). It returns chunk dicts
  `{text, source, headings, page}` — the same shape `process_rag_pipeline` produces — but
  does NOT touch the collection.
- **Store split chunks under `rag_pdfs/temp_split_chunks/`** (the same folder the full
  pipeline uses) so the user's stated layout holds. Large PDFs still get PyMuPDF page-split
  to <=8 pages via `get_pdf_chunks`.
- **UPSERT, never delete.** `collection.upsert(documents, metadatas, ids=...)` with
  unique `ids` (`upload_<uuid>_<i>`) appends to the live collection. Do NOT call
  `client.delete_collection` (that's what the one-shot rebuild does).
- **Rebuild the BM25 index after upsert** (`_rebuild_bm25()` re-reads `collection.get()`)
  or hybrid retrieval won't see the new chunks. This is the easy-to-miss step — vector
  search sees them immediately, BM25 lexical search does NOT until rebuilt.
- **Endpoint shape:** `POST /api/upload` with `UploadFile`; save to temp folder, run
  `chunk_single_pdf` in `asyncio.to_thread` (docling is CPU-bound), upsert, rebuild BM25,
  return `{ok, filename, chunks_added, total_chunks}`. Guard unsupported extensions.
- **UI:** a hidden `<input type=file>` + paperclip `<label>`; `FormData` POST; on success
  show "✅ Added N chunks" and prompt the user to ask. No separate chat turn needed — the
  next `/api/chat` query already covers the uploaded file because BM25 was rebuilt.
- **Verification recipe (real, not claimed):** generate a uniquely-marked probe PDF with
  PyMuPDF (`fitz.open().new_page().insert_text(...)`), upload it, then query its unique
  phrase and assert the answer text references only-that-PDF content. Then rebuild the
  collection from source PDFs to evict test chunks (`process_rag_pipeline` wipes + rebuilds
  to the pristine count).
