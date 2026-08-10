# RAG Project Sizing with Local Models

## Key Distinction: Embedding Model ≠ Generation Model

**MiniLM-L6-V2** (600M params, ~240MB) is an *embedding model* — it outputs vector representations for similarity search. It **cannot generate text answers** from retrieved context.

**qwythos-9b-abliterated** (9B params, 5.6GB) is a *generation model* — it reads retrieved chunks and synthesizes coherent answers. It can also function as a retriever via its 1M context window, but a dedicated embedding model is faster and cheaper for that role.

A proper RAG pipeline needs **both**: embedding model for retrieval + LLM for generation.

## Recommended RAG Stack (Local, Free)

```
Embedding (retrieval):  all-MiniLM-L6-V2 or nomic-embed-text (fast, free, ~240MB)
LLM (generation):       qwythos-9b-abliterated:Q4_K_M (1M context, strong synthesis)
Vector DB (simple):     ChromaDB (pip install, no server)
Vector DB (mid/large):  Qdrant (Docker or binary)
Reranker (optional):    bge-reranker-v2-m3 (large projects, top-k precision)
Chunking:               LangChain RecursiveCharacterTextSplitter or semantic chunking
```

## Three Tiers

| Tier | Docs | Context | LLM | Vector DB | Reranker |
|------|------|---------|-----|-----------|----------|
| **Simple** | 100-500 | 4-16K | qwythos-9b (overkill but fine) | Chroma | Not needed |
| **Mid** | 1K-10K | 50-200K | qwythos-9b | Chroma or Qdrant | Optional |
| **Large** | 100K+ | 200K-1M+ | qwythos-9b | Qdrant or Milvus | bge-reranker-v2-m3 |

## Why qwythos-9b Excels at RAG

1. **1M context window** — 4-8x more than typical 8B models (128K-256K). Fewer retrieval rounds needed; can stuff entire document sets into a single prompt.
2. **Qwen3.5 hybrid attention** — SSM state compression + sparse attention handles long context efficiently.
3. **9B params at Q4_K_M** — quality/speed sweet spot; close to Q5_K_M quality but ~1GB smaller.

## Embedding Model Comparison

| Model | Size | Speed | Accuracy | Best For |
|-------|------|-------|----------|----------|
| all-MiniLM-L6-V2 | ~240MB | Very fast | Good | Simple/mid RAG, general purpose |
| nomic-embed-text | ~270MB | Fast | Better | Mid/large RAG, longer documents |
| bge-large-en-v1.5 | ~1.3GB | Medium | Best | Large RAG, highest accuracy needed |

**Rule of thumb:** Start with MiniLM-L6-V2. Upgrade embedding model only if retrieval quality is the bottleneck (not generation quality).

## Bottleneck Diagnosis

| Symptom | Bottleneck | Fix |
|---------|-----------|-----|
| Wrong docs retrieved | Embedding/retrieval | Better embedding model, add reranker, improve chunking |
| Right docs but wrong answer | Generation/LLM | Larger context, better prompt, or bigger model |
| Answer misses cross-doc info | Chunking strategy | Use semantic chunking, increase chunk overlap |
| Too slow | Vector DB or chunk count | Use Qdrant with HNSW, add filtering, reduce corpus size |

## Quick Start: Simple RAG (Python)

```python
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer
import ollama

# Setup
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
client = PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("docs")

# Ingest
docs = ["doc1 text...", "doc2 text...", ...]
embeddings = embed_model.encode(docs).tolist()
collection.add(documents=docs, embeddings=embeddings, ids=[f"doc{i}" for i in range(len(docs))])

# Query
query = "What is RAG?"
query_embed = embed_model.encode([query]).tolist()
results = collection.query(query_embeddings=query_embed, n_results=5)
context = "\n\n".join(results["documents"][0])

response = ollama.chat(model="qwythos-9b-abliterated:Q4_K_M", messages=[
    {"role": "system", "content": f"Answer based on this context:\n{context}"},
    {"role": "user", "content": query}
])
print(response["message"]["content"])
```

## Hardware Context

Based on RTX 5070 Laptop (8GB VRAM), 16GB RAM:
- MiniLM-L6-V2 runs on CPU (negligible memory)
- qwythos-9b Q4_K_M fits in 8GB VRAM with ~2GB left for context
- ChromaDB runs in-process (no server needed)
- Qdrant needs Docker or separate process
