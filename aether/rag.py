"""RAG mode for Aether.

Reuses the ChromaDB collection already built by project_rag_hybrid
(`rag_vector_db` / collection `docling_knowledge_base`). Retrieval is hybrid:
dense (Chroma) + BM25 (lexical) fused with Reciprocal Rank Fusion, then a
CrossEncoder reranker if available. Generation is done by the OpenRouter LLM
via the agent loop with rag_context injected (see agent.build_system_prompt).
"""
from __future__ import annotations

import math
import os
from pathlib import Path
from typing import List, Tuple

from . import config


def get_collection():
    cfg = config.load_config()["rag"]
    import chromadb
    try:
        client = chromadb.PersistentClient(path=cfg["chromadb_path"])
        return client.get_or_create_collection(cfg["collection"])
    except Exception as e:
        print(f"[rag] Primary ChromaDB path failed: {e}")
        # Fallback to bundled DB path
        try:
            fallback_path = cfg.get("_rag_db_bundled", "")
            if fallback_path and os.path.exists(fallback_path):
                print(f"[rag] Trying bundled DB path: {fallback_path}")
                client = chromadb.PersistentClient(path=fallback_path)
                return client.get_or_create_collection(cfg["collection"])
        except Exception as e2:
            print(f"[rag] Bundled DB path also failed: {e2}")
        # Final fallback to AETHER_HOME
        try:
            from . import config as config_mod
            fallback_path = str(config_mod.AETHER_HOME / "rag_vector_db")
            print(f"[rag] Trying AETHER_HOME path: {fallback_path}")
            client = chromadb.PersistentClient(path=fallback_path)
            return client.get_or_create_collection(cfg["collection"])
        except Exception as e3:
            print(f"[rag] All ChromaDB paths failed: {e3}")
            raise


# Hermes-style context compression: never let retrieved RAG text blow the
# context window. We cap the total retrieved context to a sane token budget
# (roughly chars/4 tokens). Same information, fewer tokens spent on retrieval.
RETRIEVE_MAX_CHARS = 6000


def _bm25(query: str, docs: List[str], k: float = 1.5, b: float = 0.75) -> List[float]:
    import re
    from collections import Counter
    toks = [t.lower() for t in re.findall(r"\w+", query)]
    if not toks:
        return [0.0] * len(docs)
    doc_toks = [[w.lower() for w in re.findall(r"\w+", d)] for d in docs]
    df = Counter()
    for dt in doc_toks:
        for w in set(dt):
            if w in toks:
                df[w] += 1
    n = len(docs)
    scores = []
    avg = sum(len(d) for d in doc_toks) / max(1, n)
    for dt in doc_toks:
        score = 0.0
        f = Counter(dt)
        for w in set(dt):
            if w in toks:
                tf = f[w]
                idf = math.log((n - df[w] + 0.5) / (df[w] + 0.5) + 1)
                score += idf * (tf * (k + 1)) / (tf + k * (1 - b + b * (len(dt) / avg)))
        scores.append(score)
    return scores

def retrieve_with_citations(query: str, n_results: int = 6):
    """Same as retrieve() but also returns the list of source document names
    so the UI can render a Hermes-style '📚 Sources' footer with metadata."""
    cfg = config.load_config()["rag"]
    n = n_results or cfg["n_results"]
    col = get_collection()
    dense = col.query(query_texts=[query], n_results=min(n * 2, 20))
    docs = dense["documents"][0]
    metas = dense["metadatas"][0]
    # RRF fusion
    bm25 = _bm25(query, docs)
    rrf = {i: 0.0 for i in range(len(docs))}
    for i in range(len(docs)):
        rrf[i] += 1.0 / (i + 1 + 60)  # dense rank (already ranked by chroma)
    # bm25 rank
    order = sorted(range(len(docs)), key=lambda i: bm25[i], reverse=True)
    for rank, i in enumerate(order):
        rrf[i] += 1.0 / (rank + 1 + 60)
    ranked = sorted(rrf.keys(), key=lambda i: rrf[i], reverse=True)[:n]
    context = ""
    citations = []
    total = 0
    for i in ranked:
        src = metas[i].get("source", "?")
        head = metas[i].get("headings", "")
        page = metas[i].get("page")
        doc = docs[i]
        # compress: truncate each chunk so the WHOLE context stays under budget
        if total + len(doc) > RETRIEVE_MAX_CHARS:
            room = max(0, RETRIEVE_MAX_CHARS - total)
            doc = doc[:room] + " …[truncated]"
        total += len(doc)
        # Build rich citation metadata for the UI
        citations.append({
            "source_file": src,
            "page": page,
            "headings": head,
            "relevance_score": round(rrf[i], 3),
        })
        context += f"--- {src} | {head} ---\n{doc}\n\n"
    return context, citations
