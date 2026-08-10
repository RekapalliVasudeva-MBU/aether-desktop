# PyInstaller + Inno Setup — Pitfalls & Exact Fixes

Failure modes hit while freezing an AetherMind Hybrid RAG desktop app
(PyInstaller one-folder `--windowed`, pywebview UI, ChromaDB vector store,
docling PDF parsing, sentence-transformers CrossEncoder reranker). Each ran in a
clean `build_venv` (ONLY the app deps + pyinstaller — never the dev agent venv,
which bloats the bundle to several GB).

---

## 1. Emoji `print()` crashes the frozen exe (`UnicodeEncodeError`)
**Symptom:** `File "main.py", line 66 ... UnicodeEncodeError: 'charmap' codec
can't encode character '\U0001f527' ... character maps to <undefined>` at
import time.
**Cause:** `--windowed` exe inherits a cp1252 console; emoji `print()` fails.
**Fix:** at the TOP of the entry module (before any import-time emoji print):
```python
import sys
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
```

## 2. `--add-data` drops large nested data dirs
**Symptom:** `dist/<App>/rag_vector_db` is missing even though
`--add-data=rag_vector_db;rag_vector_db` was passed (Chroma's UUID subfolders
were silently omitted).
**Fix:** in `build_exe.py`, after `PyInstaller.__main__.run()`, post-sync with
`shutil.copytree`-style copy:
```python
import shutil
from pathlib import Path
OUT = Path("dist") / "AetherMindHybrid"
def _sync(src_name, dst_name=None):
    dst_name = dst_name or src_name
    src = Path(src_name)
    if not src.exists(): return
    dst = OUT / dst_name
    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.rglob("*"):
            if item.is_file():
                (dst / item.relative_to(src)).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst / item.relative_to(src))
```
Call `_sync("rag_vector_db")`, `_sync("rag_pdfs")`, `_sync("desktop/ui","ui")`.

## 3. ChromaDB dynamic imports (THE RIGHT WAY — read #8 first)
ChromaDB pulls in submodules at runtime via `importlib.import_module` that
PyInstaller can't see: `chromadb.telemetry.product.posthog`,
`chromadb.api.rust`, `chromadb.migrations.embeddings_queue`.

**DO NOT use `--collect-submodules=chromadb`** — it force-collects
`chromadb.segment.impl.vector.local_persistent_hnsw` (and `local_hnsw`), which
both do a **top-level `import hnswlib`**. If there is no hnswlib wheel for your
Python/Windows (and no C++ compiler to build one — very common on a user laptop),
the frozen exe dies with `No module named 'hnswlib'` on first `col.query()`.

**Use TARGETED hidden-imports + EXCLUDE the hnsw segment** (the web server uses
the default Rust API, which never imports the hnsw segment, so this is safe):
```
"--hidden-import=chromadb.telemetry.product.posthog",
"--hidden-import=chromadb.api.rust",
"--hidden-import=chromadb.migrations.embeddings_queue",
"--exclude-module=chromadb.segment.impl.vector.local_persistent_hnsw",
"--exclude-module=chromadb.segment.impl.vector.local_hnsw",
"--collect-submodules=onnxruntime",
"--hidden-import=tokenizers",
"--hidden-import=sentence_transformers",
```
If the exe STILL imports hnswlib after this, see #8 for the tie-out.

## 4. docling `pdf_resources` missing → "no existing pdf_resources_dir: .../_internal/docling_parse/pdf_resources/"
**Cause:** docling stores runtime PDF models in `docling_parse/pdf_resources`
inside site-packages; PyInstaller doesn't auto-place them at `<exe>/_internal/`.
**Fix (post-build copy from venv):** use `Path(__file__).parent`, NOT
`site.getsitepackages()` (which on this Windows venv returned the venv root, not
`Lib/site-packages`):
```python
_docling_res = Path(__file__).parent / "build_venv" / "Lib" / "site-packages" / "docling_parse" / "pdf_resources"
if _docling_res.is_dir():
    dst = OUT / "_internal" / "docling_parse" / "pdf_resources"
    dst.mkdir(parents=True, exist_ok=True)
    for item in _docling_res.rglob("*"):
        if item.is_file():
            (dst / item.relative_to(_docling_res)).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dst / item.relative_to(_docling_res))
```
Verify: `find dist/<App>/_internal/docling_parse/pdf_resources -type f | wc -l` == 441.

## 5. ChromaDB `is_empty` check false-positives → app rebuilds the seeded index
**Symptom:** prebuilt index was copied but the app ignored it and re-ran
`process_rag_pipeline` (slow, and failed because of #4).
**Cause:** `any(p.glob("*.bin"))` only checks the ROOT; Chroma nests segment
files in per-collection UUID subfolders.
**Fix:** recursive check in both the seeding function AND any `_is_empty_db`:
```python
return not any(p.rglob("*.bin")) and not any(p.rglob("*.parquet"))
```

## 6. Reranker `sorted` crash (not PyInstaller-specific, same class of app)
`sorted(zip(scores, docs, metas), reverse=True)` raises
`TypeError: '<' not supported between dict and dict` when scores tie (surfaces
after adding chunks to the index).
**Fix:** sort by score only:
```python
ranked = sorted(zip(scores, docs, metas), key=lambda x: x[0], reverse=True)
```

## 7. Testing a `--windowed` exe
- No console window → always redirect stdout/stderr to a log file:
  `dist/<App>/<App>.exe > test.log 2>&1 &` (background), then `tail test.log`.
- A 900 MB+ bundle boots in ~20-35s; `sleep 30` before curling the API.
- Verify: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:PORT/api/files`
  then POST a real query and stream-parse `data: {...}` SSE lines.
- To capture a real traceback (not just the error string) from a streaming
  endpoint, write `traceback.print_exc()` to a file inside the `except` block —
  PyInstaller's stdout redirect can swallow it from the log otherwise.

## 8. `No module named 'hnswlib'` — root-cause + diagnosis recipe
**Symptom:** frozen exe boots fine, but first `col.query()` / `col.get()` raises
`ModuleNotFoundError: No module named 'hnswlib'`.
**Why:** chromadb's `local_persistent_hnsw.py` / `local_hnsw.py` do
`import hnswlib` at MODULE TOP LEVEL. PyInstaller's `--collect-submodules=chromadb`
(or a hidden-import that drags them in) makes chromadb's segment factory import
those modules at runtime, and the import fails because hnswlib isn't installable
here (no wheel for cp3xx-win, no compiler to `pip install hnswlib` from sdist).
**Proof the rust API works without it:** the SAME chromadb in a normal venv
(web server) loads + queries a collection fine with hnswlib absent — because the
default Rust API (`chroma_api_impl="chromadb.api.rust.RustBindingsAPI"`) never
imports the hnsw segment. So the fix is to keep the hnsw segment OUT of the
import chain, not to install hnswlib.
**Verify which import triggers it (run in the build venv, pointing at the bundle):**
```python
import sys, importlib
sys.path.insert(0, "dist/<App>/_internal")
for m in ["chromadb", "chromadb.api.rust", "chromadb.api.models.collection",
          "chromadb.migrations.embeddings_queue",
          "chromadb.segment.impl.vector.local_persistent_hnsw"]:
    try:
        importlib.import_module(m); print("OK  ", m)
    except Exception as e:
        print("FAIL", m, "->", type(e).__name__, str(e)[:60])
```
`chromadb.api.rust` must be OK; `local_persistent_hnsw` will FAIL on hnswlib.
If `chromadb.api.models.collection` says "No module named" that's normal (it
doesn't exist as a module — don't add it as a hidden-import).
**Confirm the rust path is clean (no hnsw segment loaded after a query):**
```python
import sys, chromadb
from chromadb.utils import embedding_functions
client = chromadb.PersistentClient(path="rag_vector_db")
col = client.get_collection("docling_knowledge_base",
        embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"))
col.query(query_texts=["test"], n_results=3)
print("hnsw loaded?",
      "chromadb.segment.impl.vector.local_persistent_hnsw" in sys.modules)  # -> False
```
**Fix (in priority order):**
1. From #3: drop `--collect-submodules=chromadb`; add the 3 rust/telemetry/
   migrations hidden-imports + the 2 `--exclude-module` lines.
2. If still failing, the hidden-import `chromadb.api.rust` may be pulling the
   factory that imports the hnsw segment. Drop `--hidden-import=chromadb.api.rust`
   (the web server needs no explicit hidden-import to resolve rust lazily) and
   test; re-add only if you instead see `No module named 'chromadb.api.rust'`.
3. Last resort: drop a minimal `hnswlib` stub package into the bundle
   (`build_venv/Lib/site-packages/hnswlib/__init__.py` with empty/tolerant
   classes) so the top-level import succeeds without chromadb ever calling its
   functions in the rust-API query path.
**DO NOT** try to `pip install hnswlib` unless a prebuilt wheel exists for your
exact Python tag (check `python -m pip debug --verbose` supported tags first).

## Inno Setup (installer)
- Official installer: `https://jrsoftware.org/download.php/is.exe` (silent-capable).
- Per-user install (no admin): `PrivilegesRequired=lowest` +
  `DefaultDirName={autopf}\{#MyAppName}` + `UsedUserAreasWarning=no`.
- WebView2 dependency: pywebview needs the Microsoft WebView2 Runtime (on most
  Win10/11 already). Add a `[Code]` `InitializeWizard` that checks the registry
  key `SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8EAF-99FEFD8DB94A}`
  `pv` and offers the download page if absent.
- Build: `iscc installer.iss` → `installer_out/ProjectRAG-Setup.exe`.
