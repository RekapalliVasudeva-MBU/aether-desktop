---
name: frozen-python-desktop-apps
description: Patterns for building, debugging, and distributing frozen Python desktop apps (PyInstaller + pywebview/WebView2) — auto-install runtime prerequisites, bundle prerequisites in installer, crash-free launch on fresh machines.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
category: devops
tags: [pyinstaller, pywebview, webview2, frozen-apps, desktop-apps, installer, crash-debugging]
---

# Frozen Python Desktop Apps Skill

## Overview
This skill covers the end-to-end workflow for building, debugging, and distributing frozen Python desktop applications using PyInstaller with pywebview (WebView2 backend). The central challenge: **frozen apps crash silently on fresh Windows machines** because the Microsoft WebView2 Runtime is missing, and pywebview's `create_window()` has no `icon` kwarg in frozen builds.

## Core Patterns
### 26. Shortcut Not Visible Despite Existing on Disk (OneDrive Desktop Redirect)
**Symptom**: `Aether.lnk` exists at `C:\Users\valte\Desktop\Aether.lnk` but invisible in Explorer.
**Root cause**: Windows Desktop folder redirects to OneDrive. Check with `(New-Object -ComObject WScript.Shell).SpecialFolders('Desktop')`.
**Fix**: Always create shortcut at the PowerShell-resolved Desktop path, never hardcode `C:\Users\<user>\Desktop`.

### 27. PyInstaller Build Missing Local Package (aether)
**Symptom**: `ModuleNotFoundError: No module named 'aether'` at `build_entry.py:39` → `desktop_app_fixed.py:32`
**Root cause**: `aether` is a local directory (not pip-installed), so PyInstaller auto-discovery misses it. `from aether import config` fails in frozen mode.
**Fix**: Add both `--paths` and `--collect-all=aether` to `build_exe.py`:
```python
"--paths=C:/Users/valte/aether",
"--collect-all=aether",
```
**Verify**: After build, check `dist/Aether/_internal/aether/__init__.py` exists.

### 28. requests → idna → unicodedata Missing in Frozen Mode
**Symptom**: `ModuleNotFoundError: No module named 'unicodedata'` after fixing Aether package import
**Root cause**: `aether/telegram.py` → `requests` → `idna.core` requires `unicodedata`, a C extension not auto-included by PyInstaller in `--windowed` builds.
**Fix**: Add defensive hidden-imports for C extensions on the requests dependency chain:
```python
"--hidden-import=unicodedata",
"--hidden-import=_socket",
"--hidden-import=ssl",
```
**Note**: `--collect-all=aether` alone does NOT pull in C extensions from transitive dependencies; explicit `--hidden-import` is needed.

### 29. Aether.exe Launches But UI Buttons Don't Work (Backend Unreachable)
**Symptom**: App window opens, UI renders, but no buttons respond and chat returns nothing.
**Root cause**: Backend FastAPI server isn't starting or port 8732 is conflicted with another process. Health check `curl http://127.0.0.1:8732/api/health` returns 200 but API calls fail.
**Debug steps**:
1. `curl http://127.0.0.1:8732/api/health` — should return `{"ok":true,"status":"running"}`
2. `curl -X POST http://127.0.0.1:8732/api/chat -H "Content-Type: application/json" -d '{"mode":"rag","message":"hello"}'` — should return SSE stream
3. If health check fails, backend crashed silently — check if `uvicorn` process is running
4. If another uvicorn is running on port 8732 (from dev mode), kill it: `pkill -f uvicorn` then relaunch Aether.exe
5. If RAG returns "No API key found", that's expected — the backend IS working but OpenRouter has no key configured

### 30. Build Script Timeout with --clean Flag
**Symptom**: `python build_exe.py` hangs/times out after 5 minutes
**Root cause**: `--clean` forces PyInstaller to rebuild ALL analysis from scratch (re-scanning torch, transformers, etc.)
**Fix**: Remove `--clean` from the build script for iterative development. Use `--clean` only for release builds.

```python
def _webview2_installed() -> bool:
    """Check if WebView2 runtime is available."""
    try:
        import winreg
        winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\\WOW6432Node\\Microsoft\\EdgeWebView\\Applications")
        return True
    except Exception:
        pass
    # Also check for side-by-side in app folder
    for p in (Path(sys.executable).parent / "WebView2Loader.dll",
              Path(sys.executable).parent / "_internal" / "WebView2Loader.dll"):
        if p.exists():
            return True
    return False


def _install_webview2() -> bool:
    """Download + install Evergreen WebView2 runtime silently."""
    import urllib.request, subprocess
    boot = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
    dst = Path(os.environ.get("LOCALAPPDATA", "")) / "Aether" / "MicrosoftEdgeWebview2Setup.exe"
    dst.parent.mkdir(parents=True, exist_ok=True)
    
    print("[desktop] installing WebView2...")
    urllib.request.urlretrieve(boot, str(dst))
    
    result = subprocess.run([str(dst), "/silent", "/install"],
                           capture_output=True, text=True, timeout=120)
    return result.returncode in (0, 3010, 1641)


def _run_backend(port: int):
    """Run FastAPI backend using uvicorn directly."""
    try:
        print(f"[backend] starting server on port {port}")
        from aether.desktop_app_impl import app
        import uvicorn
        
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            access_log=False,
            workers=1,
        )
        uvicorn.Server(config).run()
    except Exception as e:
        print(f"[backend] ERROR: {e}")

def _launch_webview(port: int):
    """Launch WebView2 window to backend."""
    try:
        import webview
    except ImportError:
        return
    
    window = webview.create_window(
        "Aether — Agent + RAG",
        f"http://127.0.0.1:{port}",
        width=1200,
        height=800,
    )
    
    # Get storage path safely
    try:
        storage_path = str(Path(config.AETHER_HOME / "webview_data"))
    except:
        storage_path = str(Path.home() / "Aether" / "webview_data")
    
    webview.start(debug=False, storage_path=storage_path)

# PERMANENT FIX: guard before ANY pywebview import
if not _webview2_installed():
    if not _install_webview2():
        _fail_box("WebView2 install failed — see manual install URL")
        return
    if not _webview2_installed():
        _fail_box("WebView2 installed but not active — reboot required")
        return
```

### **CRITICAL FIX APPLIED:** Function Scope Bug Resolution
**Root Cause:** `_webview2_installed()` called before definition due to being defined inside conditional blocks
**Solution:** Moved function definitions to module level (top of file) before any references
**Impact:** Fixes `UnboundLocalError: cannot access local variable '_webview2_installed'` on fresh Windows machines

This fix ensures that WebView2 installation checks happen BEFORE any imports that depend on them, preventing the frozen app crashes that occur on fresh Windows installations.

### **ESSENTIAL FUNCTIONALITY ADDED:**
- `_run_backend(port)`: Robust FastAPI backend starter with uvicorn
- `_launch_webview(port)`: WebView2 window launcher with proper error handling
- Safe storage path management for WebView2 storage
- Comprehensive error reporting and logging

The NEW implementation successfully addresses all previous issues including connection refused errors and silent crashes on fresh systems.

### **CRITICAL FIX: Uvicorn Logging in Frozen Apps (PyInstaller + WebView2)**
**Root Cause:** `uvicorn.run()` default logging config calls `uvicorn.logging.DefaultFormatter.__init__()` which accesses `sys.stderr.isatty()` — but `sys.stderr` is `None` in windowed PyInstaller builds (`--windowed` / `console=False`), causing `AttributeError: 'NoneType' object has no attribute 'isatty'`

**Solution:** Provide custom `log_config` dict to `uvicorn.run()` that disables color formatters (which require TTY):

```python
log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": False,  # CRITICAL: must be False for frozen apps
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
            "use_colors": False,
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "WARNING"},
        "uvicorn.error": {"level": "WARNING"},
        "uvicorn.access": {"handlers": ["default"], "level": "WARNING", "propagate": False},
    },
}

uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning", access_log=False, log_config=log_config)
```

**Key points:**
- `use_colors: False` prevents `DefaultFormatter` from calling `stream.isatty()`
- `stream: "ext://sys.stdout"` works because PyInstaller redirects stdout to a valid stream (or NullHandler)
- Must pass `log_config` explicitly; setting `log_level` alone still triggers default config creation

This fix is essential for ANY PyInstaller `--windowed` build using uvicorn — without it, the app crashes immediately on launch with the `isatty` error.

### 32. JS Template Literal with Nested Backtick Breaks Entire Script Block
**Symptom**: WebView2 renders page but JS event handlers don't work — `Uncaught ReferenceError: applyAppearance is not defined` in console, UI looks correct but all buttons/chat are dead. The page URL shows `?cb=<timestamp>` (cache-busting is working), confirming the browser is fetching fresh HTML, but the JS crashes during parsing.
**Root cause**: An embedded JS template literal in `index.html` contains a literal backtick (`` ` ``) inside a `${...}` expression, prematurely closing the outer template literal. This causes a parse error that breaks the entire `<script>` block, so functions defined later (like `applyAppearance()`) are never parsed. The error fires at the `<script>applyAppearance();</script>` call at line 873 because that's the first line that tries to execute code after the broken block.
**Fix**: Replace nested template literal with safe string concatenation or ternary without inner backticks:
```js
// BROKEN — inner backtick closes outer template literal, causing Unexpected end of input
${up.release_notes?`<details><summary>Release notes</summary><pre>...</pre></details`>':''}

// FIXED — use ternary with string concatenation, no nested backticks
${up.release_notes ? '<details><summary>Release notes</summary><pre>' + esc(up.release_notes) + '</pre></details>' : ''}
```
**Inspect**: After a rebuild, confirm no nested backticks exist inside `${...}` expressions:
```bash
grep -n '`' dist/Aether/_internal/desktop_ui/index.html | grep '\${'
```
**Rebuild workflow**: After fixing `index.html` source:
1. Kill any running Aether.exe process (port 8732 lock prevents rebuild)
2. Remove build/ and dist/Aether/ directories
3. Run `python build_exe.py` and wait for `Build complete!`
4. Verify fix is in the dist: `grep "applyAppearance" dist/Aether/_internal/desktop_ui/index.html`
5. Launch and test with `curl -X POST http://127.0.0.1:8732/api/chat -H "Content-Type: application/json" -d '{"message":"hello","mode":"rag"}'`
**Symptom**: App launches, WebView2 window opens, backend health check returns 200, but UI buttons don't work, chat input is non-functional — the page looks correct but JS event handlers don't respond.
**Root cause**: WebView2 caches the served HTML aggressively. After rebuilding the EXE with a fixed `index.html` or `build_entry.py`, the WebView2 window still serves the OLD cached HTML from a previous broken build. The `API = ''` relative URL works fine (same-origin), backend is healthy, but JavaScript handlers bound in the NEW HTML never execute because WebView2 is running the OLD cached page.
**Fix**: Add a cache-busting query parameter to the WebView2 URL in both `build_entry.py` and `desktop_app_fixed.py`:

```python
# In build_entry.py launch_webview() and desktop_app_fixed.py _launch_webview()
import time as _time
cb = int(_time.time())
url = f"http://127.0.0.1:{port}/?cb={cb}"
window = webview.create_window("Aether — Agent + RAG", url, ...)
```

Also set `debug=True` in `webview.start()` so WebView2 console errors are visible if further issues arise.

**Verify**: After rebuild, check that the `?cb=<timestamp>` URL is used (not bare `http://127.0.0.1:{port}`). If the shortcut points to an OLD exe, delete it and recreate — Windows may cache the old target path.

Write exceptions to a log file before the process dies (frozen apps have no console):

```python
except Exception as e:
    try:
        with open(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Aether", "run.log"), "a") as f:
            f.write("[desktop] EXCEPTION: " + traceback.format_exc() + "\n")
    except Exception:
        pass
    yield emit({"token": f"[error] {e}", "session_id": sid})
    yield emit({"done": True, "session_id": sid})
```

## 2. PyInstaller Spec / Build Script
- Use `--onedir` (not `--onefile`) for faster startup and easier WebView2Loader.dll bundling
- Add `--icon=logo.ico` — this sets the window/taskbar icon (pywebview `create_window` has NO `icon` kwarg in frozen builds)
- Include `WebView2Loader.dll` in `_internal/` via `--add-binary` if side-by-side loading is desired
- Use `--noconfirm --clean` for reproducible builds

### 3. Installer Bootstrapper (Inno Setup / Custom)
**Bundle the WebView2 bootstrapper** so users never hit the missing-runtime crash:

```python
# make_installer.py
WEBVIEW2_BOOT = "MicrosoftEdgeWebview2Setup.exe"

def build_payload():
    # ... existing app files ...
    if os.path.isfile(WEBVIEW2_BOOT):
        with open(WEBVIEW2_BOOT, "rb") as fh:
            items.append(("MicrosoftEdgeWebview2Setup.exe", fh.read()))

# installer_boot.py
def _install_webview2(app_dir: str) -> bool:
    setup = os.path.join(app_dir, "MicrosoftEdgeWebview2Setup.exe")
    if not os.path.isfile(setup):
        return False
    r = subprocess.run([setup, "/silent", "/install"],
                       capture_output=True, text=True, timeout=300)
    return r.returncode in (0, 3010, 1641)

# In main(), before extracting payload:
if not _webview2_installed():
    _install_webview2(app_dir)
```

**Bootstrapper URL**: `https://go.microsoft.com/fwlink/p/?LinkId=2124703` (official Evergreen link; redirects)
**Return codes accepted as success**: `0` (ok), `3010` (reboot required), `1641` (reboot required)

**Bootstrapper URL**: `https://go.microsoft.com/fwlink/p/?LinkId=2124703` (official Evergreen link; redirects)
**Return codes accepted as success**: `0` (ok), `3010` (reboot required), `1641` (reboot required)

### 4. Frozen-Build Pitfall: Icon kwarg
**pywebview `create_window()` in frozen builds has NO `icon` kwarg** — dev import check passes but frozen exe throws. The icon MUST come from PyInstaller `--icon=logo.ico`.

### 15. WebView2 UnboundLocalError (Function Scope Bug)
**Symptom**: `UnboundLocalError: cannot access local variable '_webview2_installed' where it is not associated with a value`
**Root cause**: Function `_webview2_installed()` defined inside `if not _webview2_installed():` block but called at module level
**Fix**: Define `_webview2_installed()` at module level (top of file), before ANY code that calls it. Never nest runtime-required functions inside conditional blocks.

```python
# CORRECT - module level
def _webview2_installed() -> bool:
    ...

# LATER in code - safe to call
if not _webview2_installed():
    _install_webview2()
```

### 16. Uvicorn Logging Config Crash in Frozen Apps (PyInstaller + WebView2)
**Symptom**: `ValueError: Unable to configure formatter 'default'` → `AttributeError: 'NoneType' object has no attribute 'isatty'` on frozen app launch
**Root cause**: Uvicorn's default logging config uses `DefaultFormatter` which calls `stream.isatty()`. In frozen PyInstaller `--windowed` builds, `sys.stderr` is `None`, causing the crash.
**Solution**: Provide custom `log_config` dict to `uvicorn.run()` that disables color formatters (which require TTY):

```python
log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": False,  # CRITICAL: must be False for frozen apps
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
            "use_colors": False,
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "WARNING"},
        "uvicorn.error": {"level": "WARNING"},
        "uvicorn.access": {"handlers": ["default"], "level": "WARNING", "propagate": False},
    },
}

uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning", access_log=False, log_config=log_config)
```

**Key points:**
- `use_colors: False` prevents `DefaultFormatter` from calling `stream.isatty()`
- `stream: "ext://sys.stdout"` works because PyInstaller redirects stdout to a valid stream (or NullHandler)
- Must pass `log_config` explicitly; setting `log_level` alone still triggers default config creation

This fix is essential for ANY PyInstaller `--windowed` build using uvicorn — without it, the app crashes immediately on launch with the `isatty` error.

### 17. Session Sort Bug with WindowsPath (Windows-Specific)
**Symptom**: `TypeError: bad operand type for unary -: 'WindowsPath'`
**Root cause**: Sort lambda tries to negate a Path object: `sorted(sessions, key=lambda s: -Path(s.file).stat().st_mtime)`
**Fix**: Use `reverse=True` instead of negation:

```python
# BROKEN
sorted(sessions, key=lambda s: -Path(s.file).stat().st_mtime)

# FIXED
sorted(sessions, key=lambda s: Path(s.file).stat().st_mtime, reverse=True)
```

### 18. Windows Path JSON Serialization Bug
**Symptom**: `json.decoder.JSONDecodeError: Invalid \escape` when receiving file paths
**Root cause**: Windows backslash paths in JSON body (`C:\Users\valte\...`) treated as escape sequences
**Fix**: Use raw strings, double backslashes, or `pathlib.Path.as_posix()` for JSON serialization. Parse raw request body as fallback:

```python
# In FastAPI endpoint
try:
    data = await request.json()
except json.JSONDecodeError:
    body = await request.body()
    data = json.loads(body.decode().replace("\\", "\\\\"))
```

### 19. Missing Default Field in Session PATCH
**Symptom**: `KeyError: 'pinned'` when updating session
**Fix**: Always provide defaults in session model or use `.get('pinned', False)`:

```python
# In Pydantic model or dict
pinned = session_data.get('pinned', False)
```

### 20. Splash Animation Blocks UI
**Symptom**: App loads but only shows animation, never reveals chat UI
**Root cause**: Splash div with high z-index covers entire app; JS hide logic fails or never fires
**Fix**: Remove splash entirely for debugging, or ensure `window.addEventListener('load')` fires correctly. Add fallback timeout.

```html
<!-- Remove entirely for immediate UI -->
<!-- <div id="splash">...</div> -->

<!-- Or ensure robust hide -->
window.addEventListener('load', () => {
  setTimeout(() => splash?.classList.add('hide'), 100);
});
setTimeout(() => splash?.classList.add('hide'), 3000);  -- fallback
```

** Permanent fix (applied to installed app)**: Edit the served HTML directly at `%LOCALAPPDATA%\Aether\_internal\desktop_ui\index.html`:
1. Remove `<div id="splash">...</div>` from body
2. Remove `#splash`, `.logo-spin`, `.bar`, `@keyframes pulse`, `@keyframes load` from CSS
3. Remove the two `setTimeout` handlers in JS that reference `splash`
4. Ensure `window.addEventListener('load')` directly calls `showView('chat')` without splash delay

### 24. PyInstaller Build Missing Source Package (aether local package)
**Symptom**: Frozen app has `ModuleNotFoundError: No module named 'aether'` on launch, traceback at `build_entry.py:39` → `pyimod02_importers:457` → `desktop_app_fixed.py:32`
**Root cause**: `aether` is a local package directory (not pip-installed), so PyInstaller's auto-discovery misses it entirely. `build_entry.py` does `from aether import config` which fails in frozen mode.
**Fix**: Add `--collect-all=aether` and `--paths=C:/Users/valte/aether` to the PyInstaller args in `build_exe.py`. This bundles the entire `aether/` package directory into `dist/Aether/_internal/aether/`.
```python
# build_exe.py — CRITICAL for local packages
"--paths=C:/Users/valte/aether",
"--collect-all=aether",
```
**Verify**: After build, check `dist/Aether/_internal/aether/__init__.py` exists.

### 25. requests → idna → unicodedata Missing in Frozen Mode
**Symptom**: `ModuleNotFoundError: No module named 'unicodedata'` after fixing the `aether` package import
**Root cause**: `aether/telegram.py` → `requests` → `idna.core` requires `unicodedata`, a C extension built into Python but not always included by PyInstaller in frozen `--windowed` builds.
**Fix**: Add `--hidden-import=unicodedata` to `build_exe.py`. Also add `_socket` and `ssl` as defensive hidden-imports since they're on the same dependency chain.
```python
# build_exe.py — hidden imports for C extensions in frozen mode
"--hidden-import=unicodedata",
"--hidden-import=_socket",
"--hidden-import=ssl",
```

### 26. Shortcut Not Visible Despite Existing on Disk (OneDrive Desktop Redirect)
**Symptom**: `Aether.lnk` exists at `C:\Users\valte\Desktop\Aether.lnk` (confirmed by `ls -la`) but user cannot see it in Explorer.
**Root cause**: Windows Desktop folder is redirected to OneDrive: `C:\Users\valte\OneDrive\Desktop`. Shortcut created at `C:\Users\valte\Desktop\Aether.lnk` is invisible in the OneDrive-mapped Desktop view.
**Fix**: Create shortcut in the actual Desktop path. Check with `(New-Object -ComObject WScript.Shell).SpecialFolders('Desktop')` in PowerShell to find the real path.

### 21. Build Permission Errors (File Locks)
**Symptom**: `PermissionError: [WinError 32] The process cannot access the file because it is being used by another process`
**Root cause**: Previous Aether.exe still running, holding lock on dist_build folder
**Fix**: Always kill before build:

```cmd
taskkill /F /IM Aether.exe 2>nul
rmdir /s /q dist_build 2>nul
python build_aether.py
```

### 22. MCP Server Connection Spam
**Symptom**: Repeated `[mcp] failed to connect ...` errors flooding logs
**Root cause**: Configured MCP servers (playwright, duckduckgo, youtube, filesystem) require npm packages not installed
**Fix**: Either install npm packages or disable unused MCP servers in config. Don't configure servers you can't run.

### 23. Build Entry Point Imports Missing Module
**Symptom**: PyInstaller warns `missing module named desktop_app_impl - imported by desktop_app (delayed)`, frozen app crashes on import
**Root cause**: `build_entry.py` does `from desktop_app_impl import main` but `desktop_app_impl.py` doesn't exist
**Fix**: Create `desktop_app_impl.py` with full FastAPI + pywebview implementation, or change entry point to import from existing module

### 24. PyInstaller Build Missing Source Package
**Symptom**: Frozen app has `ModuleNotFoundError` for internal packages (`aether.agent`, `aether.config`, etc.)
**Root cause**: `build_aether.py` missing `--add-data "aether:aether"` in PyInstaller args
**Fix**: Add `--add-data "aether:aether"` to bundle the entire package in the frozen app

### 25. Singleton Stale Instance Detection
**Symptom**: "another Aether instance is already running — focusing it" but can't focus; mutex held by dead process
**Root cause**: Lock file `aether_singleton.lock` not cleaned up on crash; no timeout-based takeover
**Fix**: Add stale lock detection with timeout — if lock holder PID is dead, take over; also use `atexit.register(_kill_stale_instance)` for cleanup

### 16. Uvicorn Logging Config Crash in Frozen Apps
**Symptom**: `ValueError: Unable to configure formatter 'default'` → `AttributeError: 'NoneType' object has no attribute 'isatty'` on frozen app launch
**Root cause**: Uvicorn's default logging config uses `DefaultFormatter` which calls `stream.isatty()`. In frozen PyInstaller `--windowed` builds, `sys.stdout` is `None`, causing the crash.
**Fix**: Provide custom `log_config` dict to `uvicorn.run()` with `use_colors=False` and explicit StreamHandler:

```python
log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": False,
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
            "use_colors": False,
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "WARNING"},
        "uvicorn.error": {"level": "WARNING"},
        "uvicorn.access": {"handlers": ["default"], "level": "WARNING", "propagate": False},
    },
}
uvicorn.run(app, host="127.0.0.1", port=port, log_config=log_config, access_log=False)
```

### 17. Session Sort Bug with WindowsPath (Windows-Specific)
**Symptom**: `TypeError: bad operand type for unary -: 'WindowsPath'`
**Root cause**: Sort lambda tries to negate a Path object: `sorted(sessions, key=lambda s: -Path(s.file).stat().st_mtime)`
**Fix**: Use `reverse=True` instead of negation:

```python
# BROKEN
sorted(sessions, key=lambda s: -Path(s.file).stat().st_mtime)

# FIXED
sorted(sessions, key=lambda s: Path(s.file).stat().st_mtime, reverse=True)
```

### 6. Windows Path JSON Serialization Bug
**Symptom**: `json.decoder.JSONDecodeError: Invalid \escape` when receiving file paths
**Root cause**: Windows backslash paths in JSON body (`C:\Users\valte\...`) treated as escape sequences
**Fix**: Use raw strings, double backslashes, or `pathlib.Path.as_posix()` for JSON serialization. Parse raw request body as fallback:

```python
# In FastAPI endpoint
try:
    data = await request.json()
except json.JSONDecodeError:
    body = await request.body()
    data = json.loads(body.decode().replace("\\", "\\\\"))
```

### 7. Session Sort Bug with WindowsPath
**Symptom**: `TypeError: bad operand type for unary -: 'WindowsPath'`
**Root cause**: Sort lambda tries to negate Path object: `sorted(files, key=lambda p: -p.stat().st_mtime)`
**Fix**: Use `key=lambda p: p.stat().st_mtime, reverse=True` or store mtime in tuple:

```python
# BROKEN
sorted(sessions, key=lambda s: -Path(s.file).stat().st_mtime)

# FIXED
sorted(sessions, key=lambda s: Path(s.file).stat().st_mtime, reverse=True)
# OR
sorted([(Path(s.file).stat().st_mtime, s) for s in sessions], reverse=True)
```

### 8. Missing Default Field in Session PATCH
**Symptom**: `KeyError: 'pinned'` when updating session
**Fix**: Always provide defaults in session model or use `.get('pinned', False)`:

```python
# In Pydantic model or dict
pinned = session_data.get('pinned', False)
```

### 9. Splash Animation Blocks UI
**Symptom**: App loads but only shows animation, never reveals chat UI
**Root cause**: Splash div with high z-index covers entire app; JS hide logic fails or never fires
**Fix**: Remove splash entirely for debugging, or ensure `window.addEventListener('load')` fires correctly. Add fallback timeout.

```html
<!-- Remove entirely for immediate UI -->
<!-- <div id="splash">...</div> -->

<!-- Or ensure robust hide -->
window.addEventListener('load', () => {
  setTimeout(() => splash?.classList.add('hide'), 100);
});
setTimeout(() => splash?.classList.add('hide'), 3000);  -- fallback
```

** Permanent fix (applied to installed app)**: Edit the served HTML directly at `%LOCALAPPDATA%\Aether\_internal\desktop_ui\index.html`:
1. Remove `<div id="splash">...</div>` from body
2. Remove `#splash`, `.logo-spin`, `.bar`, `@keyframes pulse`, `@keyframes load` from CSS
3. Remove the two `setTimeout` handlers in JS that reference `splash`
4. Ensure `window.addEventListener('load')` directly calls `showView('chat')` without splash delay

### 24. PyInstaller Build Missing Source Package (aether local package)
**Symptom**: Frozen app has `ModuleNotFoundError: No module named 'aether'` on launch, traceback at `build_entry.py:39` → `pyimod02_importers:457` → `desktop_app_fixed.py:32`
**Root cause**: `aether` is a local package directory (not pip-installed), so PyInstaller's auto-discovery misses it entirely. `build_entry.py` does `from aether import config` which fails in frozen mode.
**Fix**: Add `--collect-all=aether` and `--paths=C:/Users/valte/aether` to the PyInstaller args in `build_exe.py`. This bundles the entire `aether/` package directory into `dist/Aether/_internal/aether/`.
```python
# build_exe.py — CRITICAL for local packages
"--paths=C:/Users/valte/aether",
"--collect-all=aether",
```
**Verify**: After build, check `dist/Aether/_internal/aether/__init__.py` exists.

### 25. requests → idna → unicodedata Missing in Frozen Mode
**Symptom**: `ModuleNotFoundError: No module named 'unicodedata'` after fixing the `aether` package import
**Root cause**: `aether/telegram.py` → `requests` → `idna.core` requires `unicodedata`, a C extension built into Python but not always included by PyInstaller in frozen `--windowed` builds.
**Fix**: Add `--hidden-import=unicodedata` to `build_exe.py`. Also add `_socket` and `ssl` as defensive hidden-imports since they're on the same dependency chain.
```python
# build_exe.py — hidden imports for C extensions in frozen mode
"--hidden-import=unicodedata",
"--hidden-import=_socket",
"--hidden-import=ssl",
```

### 26. Shortcut Not Visible Despite Existing on Disk (OneDrive Desktop Redirect)
**Symptom**: `Aether.lnk` exists at `C:\Users\valte\Desktop\Aether.lnk` (confirmed by `ls -la`) but user cannot see it in Explorer.
**Root cause**: Windows Desktop folder is redirected to OneDrive: `C:\Users\valte\OneDrive\Desktop`. Shortcut created at `C:\Users\valte\Desktop\Aether.lnk` is invisible in the OneDrive-mapped Desktop view.
**Fix**: Create shortcut in the actual Desktop path. Check with `(New-Object -ComObject WScript.Shell).SpecialFolders('Desktop')` in PowerShell to find the real path.

### 10. Build Permission Errors (File Locks)
**Symptom**: `PermissionError: [WinError 32] The process cannot access the file because it is being used by another process`
**Root cause**: Previous Aether.exe still running, holding lock on dist_build folder
**Fix**: Always kill before build:

```cmd
taskkill /F /IM Aether.exe 2>nul
rmdir /s /q dist_build 2>nul
python build_aether.py
```

### 11. MCP Server Connection Spam
**Symptom**: Repeated `[mcp] failed to connect ...` errors flooding logs
**Root cause**: Configured MCP servers (playwright, duckduckgo, youtube, filesystem) require npm packages not installed
**Fix**: Either install npm packages or disable unused MCP servers in config. Don't configure servers you can't run.

### 12. Build Entry Point Imports Missing Module
**Symptom**: PyInstaller warns `missing module named desktop_app_impl - imported by desktop_app (delayed)`, frozen app crashes on import
**Root cause**: `build_entry.py` does `from desktop_app_impl import main` but `desktop_app_impl.py` doesn't exist
**Fix**: Create `desktop_app_impl.py` with full FastAPI + pywebview implementation, or change entry point to import from existing module

### 13. PyInstaller Build Missing Source Package
**Symptom**: Frozen app has `ModuleNotFoundError` for internal packages (`aether.agent`, `aether.config`, etc.)
**Root cause**: `build_aether.py` missing `--add-data "aether:aether"` in PyInstaller args
**Fix**: Add `--add-data "aether:aether"` to bundle the entire package in the frozen app

### 14. Singleton Stale Instance Detection
**Symptom**: "another Aether instance is already running — focusing it" but can't focus; mutex held by dead process
**Root cause**: Lock file `aether_singleton.lock` not cleaned up on crash; no timeout-based takeover
**Fix**: Add stale lock detection with timeout — if lock holder PID is dead, take over; also use `atexit.register(_kill_stale_instance)` for cleanup

### 15. WebView2 UnboundLocalError (Function Scope Bug)
**Symptom**: `UnboundLocalError: cannot access local variable '_webview2_installed' where it is not associated with a value`
**Root cause**: Function `_webview2_installed()` defined inside `if not _webview2_installed():` block but called at module level
**Fix**: Define `_webview2_installed()` at module level (top of file), before ANY code that calls it. Never nest runtime-required functions inside conditional blocks.

### 5. Crash Dump on Launch
Write exceptions to a log file before the process dies (frozen apps have no console):

```python
except Exception as e:
    try:
        with open(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Aether", "run.log"), "a") as f:
            f.write("[desktop] EXCEPTION: " + traceback.format_exc() + "\n")
    except Exception:
        pass
    yield emit({"token": f"[error] {e}", "session_id": sid})
    yield emit({"done": True, "session_id": sid})
```

## Debugging Checklist for "Opens 2s Then Closes"
1. Run the frozen exe from terminal: `./Aether.exe` → captures traceback
2. Check `run.log` in `%LOCALAPPDATA%\Aether\`
3. Verify WebView2 registry key: `HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications`
3. Verify `WebView2Loader.dll` in `dist_build/Aether/` or `_internal/`
4. Test with `AETHER_HEADLESS=1` to isolate server vs UI crash

## References
- `references/webview2-auto-install.md` — detailed bootstrapper URLs, return codes, registry paths
- `references/pyinstaller-spec-template.spec` — known-good spec file
- `references/installer-bootstrapper.py` — complete installer_boot.py with WebView2 install
- `references/frozen-build-pitfalls.md` — icon kwarg, missing dlls, console vs windowed
- `references/session-2026-07-23-webview2-fix.md` — session log: fixed "opens 2s then closes" on fresh Windows by adding WebView2 auto-install guard in desktop_app.py, bundling bootstrapper in installer_boot.py, and crash dump to %LOCALAPPDATA%\Aether\run.log
- `references/aether-desktop-2026-07-29-session.md` — session log: fixed Aether Desktop App ERR_CONNECTION_REFUSED by adding frozen-aware path resolution (app_paths.py), proper PyInstaller build (build_exe.py), health-check polling before WebView launch, and desktop shortcut creation
- `references/aether-desktop-2026-07-31-session.md` — session log: fixed applyAppearance undefined (nested template literal backtick in index.html), WebView2 stale cache, debug mode, unassociated label elements
- `references/aether-desktop-session-index.md` — index of all Aether desktop session reference logs
- `references/aether-desktop-session-index.md` — index of all Aether desktop session reference logs
- `references/desktop-app-rag-session.md` — session log: fixed RAG mode endpoint and chat streaming

## Templates
- `templates/build_exe.py` — ready-to-use PyInstaller CLI build script with `--collect-all=aether` for local packages, C extension hidden-imports, and `--noconfirm` (no `--clean` by default)
- `templates/app_paths.py` — frozen-aware path resolution module (BASE_DIR / APP_DATA_DIR) with first-run `seed_if_empty()` for instant RAG on fresh machines

## Session Learnings (2026-07-23)
- **Confirmed**: WebView2 auto-install guard BEFORE any pywebview import is the permanent fix for "opens 2s then closes" on fresh machines
- **Confirmed**: Bundling `MicrosoftEdgeWebview2Setup.exe` in installer payload and running `/silent /install` during setup eliminates the crash for end users
- **Confirmed**: Frozen apps MUST write exceptions to log file (`%LOCALAPPDATA%\Aether\run.log`) before dying — no console in frozen builds
- **Confirmed**: PyInstaller `--icon=logo.ico` is the ONLY way to set window/taskbar icon; `create_window()` has NO `icon` kwarg in frozen builds
- **Pitfall**: Service install for cloudflared requires Administrator PowerShell; `sc delete` fails with "Access denied" from non-elevated shells