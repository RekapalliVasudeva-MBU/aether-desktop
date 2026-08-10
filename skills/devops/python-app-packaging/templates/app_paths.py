"""app_paths.py — frozen-aware path resolution for a PyInstaller-bundled desktop app.

Why: a frozen .exe does NOT live next to project source, and the end user must
be able to WRITE data (vector DB, uploads, settings) WITHOUT admin rights. So:
  - READ-ONLY bundled assets (UI, prebuilt index, sample PDFs) come from the exe dir.
  - WRITABLE user data lives in %LOCALAPPDATA%/<AppName> (no admin needed).
  - On first run, seed the user's data dir from the bundle (so the app is usable
    instantly instead of rebuilding the index from scratch).

Usage: import in the entry point AND the main module; point every data path at these.
"""
from pathlib import Path
import os, shutil

HERE = Path(__file__).resolve().parent

# Frozen? PyInstaller sets sys._MEIPASS; else we're running from source.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent          # the dist/<App>/ folder
else:
    BASE_DIR = HERE

APP_NAME = "AetherMindHybrid"
APP_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_NAME
BASE_DIR.mkdir(parents=True, exist_ok=True)
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- writable user data (goes to %LOCALAPPDATA%) ---
PDF_DIR = APP_DATA_DIR / "rag_pdfs"
CHROMA_DIR = APP_DATA_DIR / "rag_vector_db"
SETTINGS_PATH = APP_DATA_DIR / "rag_settings.json"

# --- read-only bundled assets (ship inside the installer next to the exe) ---
UI_DIR = BASE_DIR / "ui"
BUNDLED_PDFS = BASE_DIR / "rag_pdfs"
BUNDLED_DB = BASE_DIR / "rag_vector_db"
BUNDLED_SETTINGS = BASE_DIR / "rag_settings.json"


def seed_if_empty():
    """Copy sample PDFs + a prebuilt index from the bundle into the user's
    data dir on first run. Idempotent: skips anything already present."""
    # PDFs
    if BUNDLED_PDFS.is_dir():
        PDF_DIR.mkdir(parents=True, exist_ok=True)
        for pdf in BUNDLED_PDFS.glob("*"):
            if pdf.is_file() and not (PDF_DIR / pdf.name).exists():
                shutil.copy2(pdf, PDF_DIR / pdf.name)
    # Settings (only if user has none)
    if BUNDLED_SETTINGS.is_file() and not SETTINGS_PATH.exists():
        shutil.copy2(BUNDLED_SETTINGS, SETTINGS_PATH)
    # Prebuilt ChromaDB (only if user has none). Chroma nests data in UUID
    # subfolders, so check subdirs, not just root files.
    has_local = any(CHROMA_DIR.rglob("*.bin")) or any(CHROMA_DIR.rglob("*.parquet")) if CHROMA_DIR.is_dir() else False
    has_bundled = BUNDLED_DB.is_dir() and any(BUNDLED_DB.rglob("*"))
    if not has_local and has_bundled:
        try:
            shutil.copytree(BUNDLED_DB, CHROMA_DIR, dirs_exist_ok=True)
        except Exception as e:
            print(f"[seed] could not copy prebuilt index: {e}")
