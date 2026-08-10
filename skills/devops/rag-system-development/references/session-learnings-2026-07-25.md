# Session Learnings: 2026-07-25 — Fixing Empty ChromaDB & Server Startup Issues

## Context
Fixed a broken RAG server (project_rag) that had:
- Empty ChromaDB collection (0 chunks) — deleted during prior debugging
- BM25 index crash on empty collection (`ZeroDivisionError`)
- Port 8000 held by stale processes
- Invalid OpenRouter model (`tencent/hunyuan-a13b-instruct:free` returns 404)

## Key Fixes Applied

### 1. Guard BM25 against empty collection (server.py)
```python
# Lines 389-398: Handle empty collection gracefully
_all = collection.get()
_BM25_DOCS = _all["documents"]
_BM25_IDS = _all["ids"]

if _BM25_DOCS and len(_BM25_DOCS) > 0:
    _BM25 = BM25Okapi([_tokenize(d) for d in _BM25_DOCS])
else:
    _BM25 = None
    print("⚠️ ChromaDB collection is empty — BM25 index not built (will use semantic search only)")
```

And in both `sync_hybrid_search` and `sync_hybrid_search_with_citations`:
```python
if _BM25 is not None:
    lex_scores = _BM25.get_scores(_tokenize(clean_q))
    lex = [_BM25_IDS[i] for i in sorted(range(len(lex_scores)), key=lambda i: lex_scores[i], reverse=True)[:n_results]]
else:
    lex = []
```

### 2. Rebuild knowledge base from PDFs (main.py)
```bash
cd /c/Users/valte/project_rag && python main.py
# Processes 27 PDFs → 572 chunks, stores in ChromaDB collection "docling_knowledge_base"
```

### 3. Update OpenRouter model to verified free model (server_config.json)
```json
{
  "openrouter_model": "nvidia/nemotron-3-ultra-550b-a55b:free"
}
```
**How to verify free models:**
```bash
curl -s "https://openrouter.ai/api/v1/models" | python -c "
import json, sys
data = json.load(sys.stdin)
for m in data['data']:
    if ':free' in m['id'] or m.get('pricing', {}).get('prompt', '0') == '0':
        print(f'{m[\"id\"]} - {m.get(\"name\", \"\")}')
"
```

### 4. Kill stale processes before server start
```bash
netstat -ano | findstr :8000
# Get PID from output, then:
taskkill /F /PID <pid>
```

### 5. Cloudflare tunnel — prefer quick tunnel for local dev
```bash
# Named tunnel needs origin cert (fails without it)
cloudflared tunnel run aether-rag  # FAILS without cert.pem

# Quick tunnel — no account needed, URL changes each run
cloudflared tunnel --url http://localhost:8000  # Works immediately
```

## Remaining Issue
Chat endpoint returns "I don't have information about that in my knowledge base" despite relevant chunks existing (distances 0.30–0.45 < 0.50 cutoff). Debug next:
- Check `sync_hybrid_search_with_citations` return value
- Verify CrossEncoder rerank isn't dropping all results
- Confirm OpenRouter API call succeeds (no silent error in stream)

## Verified Working
- ✅ Server starts on :8000, health returns `chunks: 572`
- ✅ Website loads at http://127.0.0.1:8000/
- ✅ Direct ChromaDB semantic search returns relevant results
- ✅ OpenRouter free model responds correctly (tested standalone)

## Commands for Future Sessions
```bash
# Full rebuild + server start
cd /c/Users/valte/project_rag
python main.py                          # rebuild KB (slow, ~5 min)
taskkill /F /PID $(netstat -ano | findstr :8000 | awk '{print $5}') 2>nul || true
python -m uvicorn server:app --host 0.0.0.0 --port 8000 &
sleep 15 && curl -s http://127.0.0.1:8000/api/health
```