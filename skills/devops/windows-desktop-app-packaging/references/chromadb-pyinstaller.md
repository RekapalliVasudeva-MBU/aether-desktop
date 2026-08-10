# chromadb in a PyInstaller (onedir) frozen build

## Symptom
App runs from source (`python desktop_app.py`) fine, but the frozen `.exe`
fails RAG mode with:
```
[error reading index: No module named 'chromadb.api.rust']
```
After adding that hidden-import, the next run fails with:
```
[error reading index: No module named 'chromadb.telemetry.product.posthog']
```
Whack-a-mole because chromadb imports submodules dynamically at runtime
(via `chromadb.api.rust` → `chromadb_rust_bindings` + telemetry chain).

## Fix (bundle the whole package)
In `build_aether.py` (or your PyInstaller driver):
```python
import shutil, os, sys
site_pkgs = os.path.join(
    os.path.dirname(os.path.dirname(sys.executable)),
    "Lib", "site-packages", "chromadb")   # venv = .../venv/Lib/site-packages
dst = os.path.join(HERE, "chromadb_pkg")
if os.path.isdir(dst): shutil.rmtree(dst, ignore_errors=True)
shutil.copytree(site_pkgs, dst)
```
Add to the PyInstaller cmd:
```
--add-data chromadb_pkg;chromadb
--hidden-import chromadb_rust_bindings
--hidden-import tokenizers
--hidden-import onnxruntime
```
DO NOT put `tokenizers` / `onnxruntime` in `--exclude-module` — chromadb's
rust index needs them at runtime.

## Path gotchas
- `sys.executable` for a venv is `.../venv/Scripts/python.exe`.
  `os.path.dirname(sys.executable)` = `venv/Scripts` (WRONG).
  Use `os.path.dirname(os.path.dirname(sys.executable))` = `venv/` then
  `Lib/site-packages`. `site.getsitepackages()[0]` returned `venv/` too on this
  machine (virtualenv layout quirk) — prefer the explicit two-up join.

## Vector DB location fallback (config.py)
```python
def _app_dir():
    if getattr(sys, "frozen", False):
        return Path(os.path.dirname(os.path.abspath(sys.argv[0])))
    return Path(os.path.dirname(os.path.abspath(__file__))).parent
# chromadb_path precedence: RAG_DB_PATH env > bundled rag_vector_db next to exe > AETHER_HOME/rag_vector_db
bundled = _app_dir() / "rag_vector_db"
chromadb_path = os.environ.get("RAG_DB_PATH",
    str(bundled) if os.path.isdir(bundled) else str(AETHER_HOME / "rag_vector_db"))
```
This lets the installer ship `rag_vector_db/` next to `Aether.exe` so RAG works
out of the box with zero config.
