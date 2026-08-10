"""
app_paths.py — frozen-aware path resolution for Aether Desktop App.

Problem solved: a PyInstaller-frozen .exe does NOT live next to the project
source, and the user must be able to WRITE (add PDFs, rebuild the ChromaDB,
save settings) WITHOUT administrator rights. So we split paths into two groups:

  * BASE_DIR  — the install folder (read-only at runtime once installed).
                In dev this is the project dir; frozen it is the folder that
                holds the .exe + bundled ui/ + bundled sample rag_pdfs/ +
                bundled rag_vector_db/.
  * APP_DATA_DIR (User Data) — %LOCALAPPDATA%/Aether.
                Holds the user's own rag_pdfs/, rag_vector_db/, settings.
                Always writable, never under Program Files.

On first run we SEED the user data dir from the bundled assets so the app has
documents + a ready-made index out of the box (no 2-minute first-run build).
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


APP_NAME = "Aether"
DISPLAY_NAME = "Aether — Agent + RAG"


def _base_dir() -> Path:
    """Install/ bundle root. Frozen = folder holding the .exe."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


# Install folder (read-only once deployed). Bundled assets live here.
BASE_DIR: Path = _base_dir()

# Per-user data folder (always writable, no admin needed).
def _appdata_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


APP_DATA_DIR: Path = _appdata_dir()
PDF_DIR: Path = APP_DATA_DIR / "rag_pdfs"
CHROMA_DIR: Path = APP_DATA_DIR / "rag_vector_db"
SETTINGS_PATH: Path = APP_DATA_DIR / "settings.json"

# Bundled UI (shipped inside the installer next to the .exe). Dev fallback to desktop_ui.
def _ui_dir() -> Path:
    primary = BASE_DIR / "ui"
    if primary.is_dir():
        return primary
    alt = BASE_DIR / "desktop_ui"
    return alt


UI_DIR: Path = _ui_dir()

# Default settings written on first run if none exist.
DEFAULT_SETTINGS = {
    "configured": True,
    "provider": "openrouter",
    "openrouter_api_key": "",
    "openrouter_model": "openrouter/free",
    "ollama_model": "richardyoung/qwythos-9b-abliterated:Q4_K_M",
    "theme": "dark",
    "font_size": 14,
    "auto_upgrade": True,
}


def seed_if_empty() -> None:
    """Copy bundled sample PDFs + prebuilt index into the user data dir once."""
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Seed documents only if the user has none yet.
    if not any(PDF_DIR.glob("*.pdf")):
        bundled_pdfs = BASE_DIR / "rag_pdfs"
        if bundled_pdfs.is_dir():
            for f in bundled_pdfs.iterdir():
                if f.is_file():
                    try:
                        shutil.copy2(f, PDF_DIR / f.name)
                    except Exception:
                        pass

    # 2) Seed a prebuilt ChromaDB index if the user has none yet.
    has_local = any(CHROMA_DIR.iterdir()) if CHROMA_DIR.is_dir() else False
    bundled_db = BASE_DIR / "rag_vector_db"
    has_bundled = (
        bundled_db.is_dir()
        and any(bundled_db.iterdir())            # Chroma nests data in UUID subdirs
    )
    if not has_local and has_bundled:
        try:
            shutil.copytree(bundled_db, CHROMA_DIR, dirs_exist_ok=True)
        except Exception:
            pass

    # 3) Write default settings if missing.
    if not SETTINGS_PATH.exists():
        try:
            import json
            SETTINGS_PATH.write_text(json.dumps(DEFAULT_SETTINGS, indent=2))
        except Exception:
            pass


def get_settings() -> dict:
    """Load settings from user data dir, falling back to defaults."""
    import json
    if SETTINGS_PATH.exists():
        try:
            return {**DEFAULT_SETTINGS, **json.loads(SETTINGS_PATH.read_text())}
        except Exception:
            return DEFAULT_SETTINGS
    return DEFAULT_SETTINGS


def save_settings(settings: dict) -> None:
    """Save settings to user data dir."""
    import json
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))