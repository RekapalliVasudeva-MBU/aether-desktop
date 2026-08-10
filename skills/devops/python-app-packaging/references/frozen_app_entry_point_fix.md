# Frozen App Entry Point Fix (2026-07-29)

## The Critical Bug

**Problem:** Frozen executable starts backend but **no native window opens** - process runs headless.

**Root cause:** `build_entry.py` imported `app` from `desktop_app_fixed` and called `uvicorn.run(app, ...)` directly — **bypassing the WebView launcher entirely**.

The proper entry point in `desktop_app_fixed.py` is `main()` which:
1. Starts backend in a daemon thread
2. Waits 2 seconds for backend to be ready
3. Calls `_launch_webview(port)` to open the native pywebview window

## Fix Applied to `build_entry.py`

```python
# BEFORE (broken - no window)
from desktop_app_fixed import app
uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

# AFTER (correct - opens window)
from desktop_app_fixed import main
main()
```

## Backend Thread Import Fix (desktop_app_fixed.py)

The `_run_backend()` function was importing from a non-existent module in the frozen bundle:

```python
# BEFORE (broken in frozen app)
from aether.desktop_app_impl import app

# AFTER (uses local app instance)
from desktop_app_fixed import app
```

## Why This Matters for Packaging

- **Without this fix:** The exe runs `uvicorn.run()` in the main thread and blocks forever — no window ever created
- **With this fix:** The exe calls `main()` which spawns the backend thread, waits for health, then launches WebView2 native window
- **User symptom:** "App runs but nothing opens" or "Can't reach page in browser" because there IS no window

## Verification

After fix, running the frozen exe:
```
Starting Aether backend on port 8732
Launching WebView window...
```
And a native window titled "Aether — Agent + RAG" appears.

## Packaging Note

When building the frozen app with PyInstaller, ensure `pythonnet` is included as a hidden import for pywebview WinForms backend on Windows:

```bash
pyinstaller --hidden-import pythonnet --hidden-import clr ...
```

Previously excluded them and app crashed with `ModuleNotFoundError: No module named 'clr'`.