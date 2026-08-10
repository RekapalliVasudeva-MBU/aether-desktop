# build_exe.py — PyInstaller one-folder build for Aether Desktop App.
# Run with: python build_exe.py
import PyInstaller.__main__
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.argv = [
    "pyinstaller",
    "--name=Aether",
    "--onedir",
    "--windowed",          # no console window for the desktop app
    "--icon=desktop_ui/logo.ico",  # embedded EXE + taskbar icon
    "--noconfirm",
    # NO --clean for iterative dev (causes full rebuild every time)
    # Use --clean only for release builds
    # hidden imports PyInstaller can't see (dynamically imported at runtime)
    "--hidden-import=app_paths",
    "--hidden-import=webview",
    "--hidden-import=webview.platforms.winforms",
    "--hidden-import=uvicorn",
    "--hidden-import=uvicorn.loops.auto",
    "--hidden-import=uvicorn.protocols.http.auto",
    "--hidden-import=uvicorn.protocols.websockets.auto",
    "--hidden-import=uvicorn.lifespan.on",
    "--hidden-import=chromadb",
    "--hidden-import=chromadb.api",
    "--hidden-import=chromadb.api.models",
    "--hidden-import=chromadb.api.models.Collection",
    "--hidden-import=chromadb.config",
    "--hidden-import=sentence_transformers",
    "--hidden-import=sentence_transformers.models.Transformer",
    "--hidden-import=sentence_transformers.modules.Transformer",
    "--hidden-import=sentence_transformers.modules.Pooling",
    "--hidden-import=rank_bm25",
    "--hidden-import=ollama",
    "--hidden-import=openai",
    "--hidden-import=docling",
    "--hidden-import=docling.document_converter",
    "--hidden-import=docling.datamodel",
    "--hidden-import=docling.chunking",
    "--hidden-import=transformers",
    "--hidden-import=transformers.models.auto",
    "--hidden-import=fitz",
    "--collect-all=aether",
    "--paths=C:/Users/valte/aether",
    "--hidden-import=unicodedata",
    "--hidden-import=_socket",
    "--hidden-import=ssl",
    # bundled data: UI + sample docs + prebuilt index so first run is instant
    "--add-data=desktop_ui;desktop_ui",
    "--add-data=rag_pdfs;rag_pdfs",
    "--add-data=rag_vector_db;rag_vector_db",
    # entry point
    "build_entry.py",
]

PyInstaller.__main__.run()

# PyInstaller's --add-data occasionally omits large nested data dirs
# (Chroma's UUID subfolders). Copy the prebuilt index + sample docs
# into the bundle unconditionally so first-run seeding works out of the box.
import shutil

OUT = PROJECT_ROOT / "dist" / "Aether"

def _sync(src_name, dst_name=None):
    dst_name = dst_name or src_name
    src = PROJECT_ROOT / src_name
    if not src.exists():
        return
    dst = OUT / dst_name
    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.rglob("*"):
            if item.is_file():
                rel = item.relative_to(src)
                tgt = dst / rel
                tgt.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, tgt)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

_sync("rag_vector_db")
_sync("rag_pdfs")
_sync("desktop_ui", "desktop_ui")
print("BUNDLE DATA SYNCED ->", OUT)