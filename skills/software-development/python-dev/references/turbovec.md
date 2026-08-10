# turbovec — Fast Vector Search for RAG

**Source:** https://github.com/RyanCodrai/turbovec
**Paper:** TurboQuant (ICLR 2026) — https://arxiv.org/abs/2504.19874
**PyPI:** `pip install turbovec` (v0.7.1 as of June 2026)

## What It Is

Rust-based vector index with Python bindings. Implements Google Research's TurboQuant algorithm:
- **16x less RAM** than float32 (10M docs: 31 GB → 4 GB)
- **12–20% faster** than FAISS on ARM, matches/beats on x86
- **No training phase** — vectors indexed on ingest
- **Filtered search** at SIMD kernel level (pass allowlist to `search()`)
- **Pure local** — no managed service, fully air-gapped RAG

## Installation

```bash
pip install turbovec
pip install turbovec[langchain]  # LangChain integration
```

## API Reference

### TurboQuantIndex (primary)

```python
import turbovec
import numpy as np

index = turbovec.TurboQuantIndex(dim=1536, bit_width=4)
vectors = np.random.randn(1000, 1536).astype(np.float32)
index.add(vectors)

query = np.random.randn(1, 1536).astype(np.float32)
scores, indices = index.search(query, k=10)

index.write("my_index.tv")
loaded = turbovec.TurboQuantIndex.load("my_index.tv")
```

### IdMapIndex (custom IDs)

```python
index = turbovec.IdMapIndex(dim=1536, bit_width=4)
ids = np.arange(1000, dtype=np.uint64)  # MUST be uint64
index.add_with_ids(vectors, ids)
scores, result_ids = index.search(query, k=10)
index.remove(42)  # O(1) delete
```

### Filtered/Hybrid Search

```python
allowed = np.array([10, 20, 30, 40, 50], dtype=np.uint64)
scores, ids = index.search(query, k=5, allowlist=allowed)
```

## Windows Notes

- PyPI wheel works on Windows
- Use Windows paths (not `/tmp`) for persistence
- IdMapIndex IDs must be `uint64` numpy array — `int64` and `list` both fail

## When to Use Over FAISS

| Scenario | Recommendation |
|----------|---------------|
| Memory-constrained RAG | turbovec (16x less RAM) |
| Latency-sensitive search | turbovec (faster SIMD kernels) |
| Need filtered search | turbovec (kernel-level allowlist) |
| Quick prototyping | Either works |
