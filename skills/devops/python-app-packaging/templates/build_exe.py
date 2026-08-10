# build_exe.py — PyInstaller one-folder build for a desktop app.
# Run with the CLEAN build venv:  build_venv\Scripts\python.exe build_exe.py
import PyInstaller.__main__
import sys
from pathlib import Path
import shutil

APP_NAME = "AetherMindHybrid"   # <-- edit
ENTRY = "desktop/desktop_app.py"  # <-- edit to your entry point

sys.argv = [
    "pyinstaller",
    f"--name={APP_NAME}",
    "--onedir",
    "--windowed",          # no console window for the desktop app
    "--noconfirm",
    "--clean",
    # hidden imports PyInstaller can't see (dynamically imported at runtime)
    "--collect-submodules=chromadb",
    "--collect-submodules=onnxruntime",
    "--hidden-import=tokenizers",
    "--hidden-import=sentence_transformers",
    # bundled data: UI + sample docs + prebuilt index so first run is instant
    "--add-data=desktop/ui;ui",
    "--add-data=rag_pdfs;rag_pdfs",
    "--add-data=rag_vector_db;rag_vector_db",
    # entry point
    ENTRY,
]

PyInstaller.__main__.run()

# PyInstaller --add-data occasionally omits large nested data dirs (Chroma's
# UUID subfolders). Copy the prebuilt index + sample docs + UI into the bundle
# unconditionally so first-run seeding works out of the box.
OUT = Path("dist") / APP_NAME

def _sync(src_name, dst_name=None):
    dst_name = dst_name or src_name
    src = Path(src_name)
    if not src.exists():
        return
    dst = OUT / dst_name
    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.rglob("*"):
            if item.is_file():
                (dst / item.relative_to(src)).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst / item.relative_to(src))
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

_sync("rag_vector_db")
_sync("rag_pdfs")
_sync("desktop/ui", "ui")
# docling's runtime PDF resources must sit at <exe>/_internal/docling_parse/
# so the frozen app can parse PDFs without a rebuild. Copy from the venv.
# NOTE: do NOT use site.getsitepackages() — on some Windows venvs it returns the
# venv root, not Lib/site-packages.
_docling_res = Path(__file__).parent / "build_venv" / "Lib" / "site-packages" / "docling_parse" / "pdf_resources"
if _docling_res.is_dir():
    dst = OUT / "_internal" / "docling_parse" / "pdf_resources"
    dst.mkdir(parents=True, exist_ok=True)
    for item in _docling_res.rglob("*"):
        if item.is_file():
            (dst / item.relative_to(_docling_res)).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dst / item.relative_to(_docling_res))
print("BUNDLE DATA SYNCED ->", OUT)
