# Answer-Quality Recipe — exact artifacts

## System prompt template (teaching style, few-shot)
```
You are an expert AI Engineering Assistant teaching a learner.
Answer the user's question using ONLY the CONTEXT below. Write the final answer
directly — no meta-commentary, no "Looking at the CONTEXT", no narration.
Give a SUBSTANTIVE explanation (at least 3-4 sentences) that uses the specific
details, examples, and analogies present in the CONTEXT. Do NOT stop at a one-line
definition when the CONTEXT contains more.
If the fact is absent from the CONTEXT, say so briefly. Do not use outside knowledge.
Never mention chunk numbers, source labels, or section markers.

EXAMPLE
Question: what is rag?
Good answer: RAG (Retrieval-Augmented Generation) lets an LLM look up relevant
information from your own data before generating an answer. Think of it like an
open-book vs closed-book exam: without RAG the model only uses what it was trained
on (risking hallucination and stale knowledge), while with RAG it retrieves the
right passages first and answers from them. The typical pipeline is: load documents,
split them into chunks, embed the chunks into vectors, store them in a vector
database, then at query time retrieve the most similar chunks and feed them to the
LLM as context.

CONTEXT:
{retrieved_context}
```

Honest fallback (when no chunk passes cutoff):
```
You are a retrieval-augmented assistant. No relevant context was found in the
knowledge base for this question. Reply exactly with: "I don't have information
about that in my knowledge base." Do NOT use outside knowledge and do NOT add
anything else.
```

## Retrieval code shape (Python)
```python
results = col.query(query_texts=[clean_q], n_results=6)
dists = results.get("distances", [[]])[0]
ctx = ""
for i, doc in enumerate(results["documents"][0]):
    if not doc or not doc.strip():
        continue
    if i < len(dists) and dists[i] > 0.50:   # relevance cutoff
        continue
    clean_doc = "\n".join(
        ln for ln in doc.splitlines()
        if not ln.strip().startswith("--- Chunk")   # strip metadata markers
    ).strip()
    if clean_doc:
        ctx += clean_doc + "\n\n"
had_context = bool(ctx.strip())
```

## ChromaDB distance calibration (MiniLM-L6-v2, cosine distance)
Measured on a RAG tutorial PDF corpus (578 chunks):
| Query | Top-1 dist | Verdict |
|-------|-----------|---------|
| what is rag | 0.306 | relevant |
| explain rag | 0.308 | relevant |
| claude code leaked source files | 0.295 | relevant (doc IS in KB) |
| refund policy | 0.379 | relevant |
| banana cultivation in south america | >0.50 | off-topic -> fallback |

Rule: 0.50 cutoff cleanly separates in-KB queries (0.29-0.48) from out-of-KB (>0.50).
Tune per embedding model if you swap models.

## Before / after (9B abliterated local model, "what is rag")
BEFORE (weak prompt, "Be concise", chunk labels sent):
> "RAG = Retrieval-Augmented Generation (Chunk 3)"  <- leak + thin

AFTER (teaching prompt + cutoff + strip + few-shot):
> "RAG stands for Retrieval-Augmented Generation. It works by first retrieving
> relevant information from your own data before generating an answer, which
> grounds the model in real documents and reduces hallucination. Modern systems
> use hybrid retrieval that combines multiple approaches to improve accuracy,
> speed, and cost... Newer variants extend this further with multimodal RAG and
> Agentic RAG, showing how the basic idea continues to evolve."

No "Chunk" leak, no narration, 4 sentences, grounded.
