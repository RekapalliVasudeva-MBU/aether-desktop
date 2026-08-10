# Aether Desktop App — 2026-07-29 Session Summary

**Problem**: Aether Desktop App ("Aether.exe") built with PyInstaller was showing "ERR_CONNECTION_REFUSED" in its native WebView2 window, and no desktop shortcut was created. The app would open but fail to connect to its own FastAPI backend on 127.0.0.1:8732.

**Root Causes Found**:
1. **Build script was broken** — `build_aether.py` only copied files, didn't run PyInstaller. No actual frozen exe was created.
2. **No frozen-aware paths** — Code used hardcoded paths (`config.AETHER_HOME`) that don't work when frozen.
3. **Missing bundled assets** — No `rag_pdfs` or `rag_vector_db` bundled for first-run RAG.
4. **Backend not ready before WebView launch** — WebView tried to load before uvicorn bound to port.

**Fixes Applied** (matching working `project_rag_hybrid` pattern):
1. **Created `app_paths.py`** — Frozen-aware path resolution (`BASE_DIR` / `APP_DATA_DIR`) with `seed_if_empty()` for instant first-run RAG
2. **Created `build_exe.py`** — Proper PyInstaller CLI build with `--add-data` for `desktop_ui`, `rag_pdfs`, `rag_vector_db`
3. **Updated `aether/config.py`** — Uses `app_paths.APP_DATA_DIR` instead of hardcoded paths
4. **Updated `build_entry.py`** — Waits for `/api/health` before launching WebView (polling with timeout)
5. **Created desktop shortcut** — PowerShell script creates `Aether.lnk` on Desktop pointing to `dist/Aether/Aether.exe`

**Verification**:
- Build: `python build_exe.py` → Creates `dist/Aether/Aether.exe` (~171MB)
- Health check: `curl http://127.0.0.1:8732/api/health` → `{"ok":true,"status":"running"}`
- Chat endpoint: `POST /api/chat` with `mode=rag` → Returns SSE stream (needs OPENROUTER_API_KEY configured)
- Shortcut: `Aether.lnk` created on Desktop with correct icon

**Key Architecture Pattern** (from project_rag_hybrid):
```
BASE_DIR (frozen: exe folder)          → read-only bundle assets
APP_DATA_DIR (%LOCALAPPDATA%/Aether)   → writable user data (PDFs, ChromaDB, settings)
seed_if_empty() on first run           → copies bundled PDFs + prebuilt index to APP_DATA_DIR
```

This pattern ensures the app works out-of-the-box on any fresh Windows machine without admin rights, build steps, or manual configuration.