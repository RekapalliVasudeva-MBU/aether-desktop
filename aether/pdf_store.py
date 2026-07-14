"""PDF management for Aether's RAG knowledge base.

Lets the user see which PDFs are indexed, add new ones (docling -> chunks ->
ChromaDB), remove a PDF, and rebuild the whole collection from the tracked
source PDFs. The ChromaDB collection is the same one the agent queries in
rag.retrieve(), so changes show up immediately in RAG chat.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import List

from . import config, rag


def _collection():
    return rag.get_collection()


def list_pdfs() -> List[str]:
    """Return unique source PDF paths currently indexed in the collection."""
    try:
        col = _collection()
        res = col.get(include=["metadatas"])
        srcs = sorted({m.get("source") for m in (res.get("metadatas") or []) if m.get("source")})
        return srcs
    except Exception as e:
        return [f"[error reading index: {e}]"]


def _chunk_markdown(md: str, max_chars: int = 1200) -> List[str]:
    paras = [p.strip() for p in re.split(r"\n{2,}", md) if p.strip()]
    chunks, buf = [], ""
    for p in paras:
        if len(buf) + len(p) < max_chars:
            buf = (buf + "\n\n" + p).strip()
        else:
            if buf:
                chunks.append(buf)
            buf = p
    if buf:
        chunks.append(buf)
    return [c for c in chunks if len(c) > 40]


def add_pdf(path: str) -> dict:
    """Ingest a PDF into the collection. Returns a status dict."""
    p = Path(path).expanduser()
    if not p.exists():
        return {"ok": False, "error": f"file not found: {p}"}
    try:
        from docling.document_converter import DocumentConverter
        res = DocumentConverter().convert(str(p))
        md = res.document.export_to_markdown()
    except Exception as e:
        return {"ok": False, "error": f"docling failed: {e}"}
    chunks = _chunk_markdown(md)
    if not chunks:
        return {"ok": False, "error": "no text extracted from PDF"}
    col = _collection()
    stem = p.stem
    ids = [f"{stem}_{uuid.uuid4().hex[:8]}" for _ in chunks]
    metas = [{"source": str(p), "headings": ""} for _ in chunks]
    col.add(ids=ids, documents=chunks, metadatas=metas)
    return {"ok": True, "chunks": len(chunks), "source": str(p)}


def remove_pdf(path: str) -> dict:
    """Delete all chunks belonging to a source PDF."""
    try:
        col = _collection()
        col.delete(where={"source": path})
        return {"ok": True, "source": path}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def rebuild() -> dict:
    """Re-ingest every tracked source PDF from scratch."""
    pdfs = [s for s in list_pdfs() if s and not s.startswith("[")]
    if not pdfs:
        return {"ok": False, "error": "no source PDFs tracked"}
    try:
        col = _collection()
        col.delete(where={})
    except Exception:
        pass
    added = 0
    for pdf in pdfs:
        r = add_pdf(pdf)
        if r.get("ok"):
            added += r["chunks"]
    return {"ok": True, "pdfs": len(pdfs), "chunks": added}
