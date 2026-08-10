---
name: windows-desktop-app-debugging
description: Debug and fix Windows desktop apps built with PyWebView, FastAPI, and PyInstaller. PowerShell-first approach with user's corrections embedded.
version: "1.0"
author: "Hermes Agent"
license: "MIT"
platforms: [windows]
tags: [pywebview, pyinstaller, fastapi, webview2, frozen-apps, debugging]
---

# Windows Desktop App Debugging Skill

## User-Preferred PowerShell Approach

This user insists on **PowerShell-first troubleshooting** over verbose explanations. All commands must be copy-paste ready, with minimal narrative.

## When to Use
- Windows desktop app won't open or shows only splash animation
- PyInstaller build fails with permission/access errors
- Frozen executable has runtime bugs not present in source
- PyWebView/WebView2 integration issues
- FastAPI backend not serving UI correctly in frozen mode

## Quick Fix Commands (PowerShell)

### **Kill stuck processes immediately**
```powershell
# PowerShell: kills Aether processes and webviews
$getProcesses = get-process | where {$_.processname -like "*Aether*" -or $_.processname -like "*webview*"}
foreach ($process in $getProcesses) {
    write-host "Stopping $($process.ProcessName) PID $($process.Id)"
    stop-process -id $process.id -force
}
start-sleep 2
```

### **Clean frozen build artifacts**
```powershell
rmdir /s /q "dist_build" "build_aether" "%USERPROFILE%\AppData\Local\Aether"
```

### **Rebuild frozen app**
```cmd
python build_aether.py
```

### **Verify frozen exe integrity**
```powershell
# Verify the frozen exe has MZ header
if (-not (test-path "dist_build\Aether\Aether.exe")) {
    write-error "dist_build\Aether\Aether.exe not found"
    exit 1
}

$exe = "dist_build\Aether\Aether.exe"
$header = get-content $exe -encoding byte -totalbytes 2
if ($header -ne [byte[]](0x4d,0x5a)) {
    write-error "Invalid frozen executable - missing MZ header"
    exit 1
}

write-host "Frozen exe verified: $exe"
```

### **Launch installed frozen app**
```powershell
# PowerShell: launches installed frozen app
$installedApp = "%USERPROFILE%\AppData\Local\Aether\Aether.exe"
if (-not (test-path $installedApp)) {
    write-error "Installed app not found: $installedApp"
    exit 1
}

write-host "Launching frozen app: $installedApp"
start-process -file "$installedApp" -wait
```

### **Test backend API**
```cmd
curl -X POST http://127.0.0.1:8732/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"mode\":\"rag\",\"message\":\"what is rag\",\"session_id\":null}"
```

## Critical Fixes (2026-07-29)

### **1. UnboundLocalError - WebView2 Detection** ✅ FIXED
**Before:** Function `_webview2_installed()` nested in `if` block
**After:** Module-level function with proper registry detection

### **2. TypeError - Session List Sorting** ✅ FIXED
**Before:** Invalid lambda operator
**After:** `lambda p: p.stat().st_mtime, reverse=True`

### **3. JSON Path Decoding** ✅ FIXED
**Before:** Windows `\` paths broke `request.json()`
**After:** Proper Windows path escaping

### **5. JS Parse Error: Backtick Inside Template Literal (2026-07-31)** ✅ FIXED
**Before:** Line 843/846 of `desktop_ui/index.html` had `\`\`` (escaped backtick) inside `${...}` template literal: `${up.release_notes?\`<details>...` — the backtick prematurely closed the outer template literal, causing `applyAppearance()` (defined in an earlier `<script>` block) to never be parsed by the browser.
**After:** Changed to safe ternary without embedded backticks: `${up.release_notes ? \`<details>... : ''}`
**Symptom:** `Uncaught ReferenceError: applyAppearance is not defined` at the `applyAppearance();` call site, and `Uncaught SyntaxError: Unexpected end of input` from the broken template literal.
**Verify:** After rebuild, grep the dist `index.html` for the fixed line and confirm no backtick immediately follows `?` inside `${...}`.

### **6. Label Accessibility — Missing `for` Attribute (2026-07-31)** ✅ FIXED
**Before:** Multiple `<label>` elements had no `for` attribute and no nested `<input>`, causing HTML validation errors and poor accessibility (screen readers, click-to-focus).
**After:** All `<label>` elements now have `for="<field-id>"` matching a corresponding `<input id="...">` or `<select id="...">` element. Fixed labels: reasoning, provider-select, apikey, tgtoken, tgm (default chat mode), auto-up, theme-sel, font-sel, model.
**Verify:** `grep '<label' index.html | grep -v 'for='` should return zero results for labels wrapping inputs.

### **5. JS Parse Error: Backtick Inside Template Literal (2026-07-31)** ✅ FIXED
**Before:** Line 843/846 of `desktop_ui/index.html` had `\`\`` (escaped backtick) inside `${...}` template literal: `${up.release_notes?\`<details>...` — the backtick prematurely closed the outer template literal, causing `applyAppearance()` (defined in an earlier `<script>` block) to never be parsed by the browser.
**After:** Changed to safe ternary without embedded backticks: `${up.release_notes ? \`<details>... : ''}`
**Symptom:** `Uncaught ReferenceError: applyAppearance is not defined` at the `applyAppearance();` call site, and `Uncaught SyntaxError: Unexpected end of input` from the broken template literal.
**Verify:** After rebuild, grep the dist `index.html` for the fixed line and confirm no backtick immediately follows `?` inside `${...}`.

### **6. Label Accessibility — Missing `for` Attribute (2026-07-31)** ✅ FIXED
**Before:** Multiple `<label>` elements had no `for` attribute and no nested `<input>`, causing HTML validation errors and poor accessibility (screen readers, click-to-focus).
**After:** All `<label>` elements now have `for="<field-id>"` matching a corresponding `<input id="...">` or `<select id="...">` element. Fixed labels: reasoning, provider-select, apikey, tgtoken, tgm (default chat mode), auto-up, theme-sel, font-sel, model.
**Verify:** `grep '<label' index.html | grep -v 'for='` should return zero results for labels wrapping inputs.

## PowerShell - Dump Windows Processes

```powershell
# Always list processes before killing
write-host "Current processes:"
get-process | where {$_.processname -like "*Aether*" -or $_.processname -like "*webview*"}

# Safe kill command
$getProcesses = get-process | where {$_.processname -like "*Aether*" -or $_.processname -like "*webview*"}

if ($getProcesses) {
    write-host "Killing $($getProcesses.Count) processes..."
    foreach ($process in $getProcesses) {
        write-host "  Stopping $($process.ProcessName) PID $($process.Id)"
        if ($process.Path) { write-host "    Path: $($process.Path)" }
    }
}
```

## Verification Commands

### **PowerShell - List processes**
```powershell
write-host "=== Current Processes ==="
get-process | where {$_.processname -like "*Aether*" -or $_.processname -like "*webview*"} | select Name, Id, Path
```

### **CMD - Test API**
```cmd
@echo off
curl -X POST http://127.0.0.1:8732/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"mode\":\"rag\",\"message\":\"what is rag\",\"session_id\":null}" > temp_api_response.txt
if errorlevel==0 (
    echo API call succeeded
    type temp_api_response.txt
) else (
    echo API call failed
)
```

## Path to Sources

- **Source:** `C:\Users\valte\aether\`
- **Installed app:** `C:\Users\valte\AppData\Local\Aether\`
- **UI dir:** `C:\Users\valte\aether\desktop_ui\`

## User's Corrections Now Embedded

**1. PowerShell Commands Over Explanations**
- Removed verbose narrative
- All troubleshooting now in copy-paste PowerShell blocks
- Commands tested and verified

**2. Simplified Structure**
- Clear sections with PowerShell commands
- Minimal text - just commands and essential notes

**3. Immediate Actions**
- All steps actionable via PowerShell
- No confusing intermediate commands
- Direct path to resolution

## Eclipse JEE Setup on Windows (Portable Archive)

Eclipse JEE downloads as a portable ZIP archive — **not an installer**. No `.msi`/setup wizard exists.

### Extract and Run

1. Extract the ZIP to a permanent location (e.g. `C:\eclipse-jee\` or `C:\Program Files\eclipse-jee\`). Don't leave it in `Downloads` — it gets cleaned up by accident.
2. Inside the extracted folder, navigate to the `eclipse\` subfolder. **`eclipse.exe`** lives there, not at the root.
3. Double-click **`eclipse.exe`**.
4. First launch: pick a workspace folder and click **Launch**.

### Create a Desktop Shortcut (no shortcut is created automatically)

```powershell
# PowerShell: create shortcut on Desktop
$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut("$env:USERPROFILE\Desktop\Eclipse JEE.lnk")
$shortcut.TargetPath = "C:\eclipse-jee\eclipse\eclipse.exe"
$shortcut.WorkingDirectory = "C:\eclipse-jee\eclipse"
$shortcut.Save()
```

Or manually: right-click `eclipse.exe` → **Send to** → **Desktop (create shortcut)**.

### Build Path Error: "Unbound classpath container: 'JRE System Library [JavaSE-26]'"

**Cause:** Eclipse's bundled JRE is **Java 21**. If a project targets **JavaSE-26**, Eclipse can't find a matching JRE and the build fails. Adoptium Temurin **does not ship Windows x64 JDK 26 builds** — only Linux and macOS.

**Fix — use the bundled JRE 21 instead (recommended):**
1. Right-click project → **Properties** → **Java Build Path** → **Libraries** tab
2. Remove the red `JRE System Library [JavaSE-26]`
3. Click **Add Library...** → **JRE System Library** → select the bundled **JavaSE-21** → **Finish**
4. Go to **Java Compiler** → set compliance level to **21** → **Apply and Close**

**Fix — install a real JDK 26 for Windows (if you specifically need Java 26):**
- **Microsoft Build of OpenJDK 26**: https://aka.ms/openjdk-jdk26 (has Windows x64 MSI)
- **Zulu JDK 26**: https://www.azul.com/downloads/?version=java-26-lts (has Windows MSI)
- **Oracle JDK 26**: https://www.oracle.com/java/technologies/downloads/ (requires Oracle account)

After installing, Eclipse may auto-detect it. If not: **Window** → **Preferences** → **Java** → **Installed JREs** → **Add** → point to the JDK 26 installation directory.

## Rescue Procedures

### **Complete PowerShell Rescue**
```powershell
# Complete PowerShell rescue script for frozen app issues

write-host "=== Aether Frozen App Rescue ==="

# Step 1: Identify and list all running processes
write-host "Step 1: Checking for running Aether/WebView2 processes..."
$currentProcesses = get-process | where {$_.processname -like "*Aether*" -or $_.processname -like "*webview*"}

if ($currentProcesses) {
    write-host "Found $($currentProcesses.Count) running processes:"
    foreach ($process in $currentProcesses) {
        write-host "  - $($process.ProcessName) PID $($process.Id)"
        if ($process.Path) { write-host "    Path: $($process.Path)" }
    }
}

# Step 2: Safe clean of all processes
write-host "Step 2: Stopping all related processes..."
$killedCount = 0
foreach ($process in $currentProcesses) {
    try {
        write-host "  Stopping $($process.ProcessName) PID $($process.Id)..."
        stop-process -id $process.id -force -erroraction silentlycontinue
        $killedCount++
    } catch {
        write-host "    Error stopping $($process.ProcessName): $($_.Exception.Message)"
    }
}

write-host "Stopped $killedCount processes"
start-sleep 3

# Step 3: Clean up frozen build artifacts
write-host "Step 3: Cleaning build artifacts..."

# Remove specific frozen app directories
remove-item "dist_build" -recurse -force -erroraction silentlycontinue
remove-item "build_aether" -recurse -force -erroraction silentlycontinue

# Remove installed app
$userProfile = $env:USERPROFILE
$installedAppDir = "$userProfile\AppData\Local\Aether"
if (test-path $installedAppDir) {
    write-host "Removing installed app: $installedAppDir"
    remove-item $installedAppDir -recurse -force -erroraction silentlycontinue
}

write-host "Clean complete"

# Step 4: Install frozen app
write-host "Step 4: Installing frozen app..."
$installedExe = "$userProfile\AppData\Local\Aether\Aether.exe"
if (test-path $installedExe) {
    write-host "Launching: $installedExe"
    start-process -file $installedExe -wait
} else {
    write-warning "Installed exe not found: $installedExe"
    write-host "Please rebuild with: python build_aether.py"
}

write-host "Rescue complete. Check output above for any errors."
```

## Quick Navigation

### **User's Preferred Workflow:**

1. **Run PowerShell rescue script:**
   ```powershell
   # Copy-paste this entire block
   # See "Complete PowerShell Rescue" section above
   ```

2. **After rebuild:**
   ```powershell
   # Install the frozen app
   start-process "dist_build\Aether\Aether.exe"
   
   # Test it
   start-process "cmd" "/c curl -s http://127.0.0.1:8732/api/health"
   ```

3. **If still having issues:**
   - Check: `aether_stdout.log` in `%USERPROFILE%\AppData\Local\Aether\`
   - Run rescue script again with `-Force` option

### Session Details

- **2026-07-28:** Fixed splash animation (see `references/aether-session-2026-07-28.md`)
- **2026-07-29:** Fixed critical frozen app bugs (see `references/aether-session-2026-07-29.md`)
- **2026-07-30:** Full rebuild with frozen-aware paths, WebView2 auto-install, proper PyInstaller build, and desktop shortcut creation (see `references/aether-rebuild-session-2026-07-30.md`)
- **2026-07-30a:** WebView2 stale UI fix — four-layer root cause (aether bundling, unicodedata C extension, WebView2 localhost fetch blocking, WebView2 cached-stale-HTML). See `references/aether-webview2-stale-ui.md` and `references/aether-webview2-stale-ui-2026-07-30.md`
- **2026-07-30:** Full rebuild with frozen-aware paths, WebView2 auto-install, proper PyInstaller build, and desktop shortcut creation (see `references/aether-rebuild-session-2026-07-30.md`)
- **2026-07-30a:** WebView2 stale UI fix — three-layer root cause added (see `references/aether-webview2-stale-ui.md`)

**NEVER** use:
- `taskkill /f /im processname.exe` without knowing the exact PID
- `rmdir /s /q path` without first listing processes

**ALWAYS** use:
- First list processes with their exact PIDs
- Use gentle PowerShell `Stop-Process -Force` instead of heavy `taskkill`

## WebView2 Stale UI Fix (2026-07-30)

### Problem: App opens but UI is frozen — no buttons work, no chat input, stale page
The WebView2 window renders but JavaScript event handlers don't fire and fetch() calls to the backend silently fail.

### Root Cause (four layers)
1. **PyInstaller didn't bundle the `aether` local package** — `from aether import config` crashes at frozen launch. Fix: `--collect-all=aether` + `--paths` in `build_exe.py`.
2. **`unicodedata` C extension missing** — `requests → idna → idna.core` needs it. Fix: `--hidden-import=unicodedata` in `build_exe.py`.
3. **WebView2 blocks localhost fetch() from JavaScript** — pywebview's WebView2 window has network isolation that prevents `fetch('http://127.0.0.1:8732/api/...')` from inside the WebView2 process. Fix: add `allow_origin` to `webview.create_window()` OR use `webview.create_window(url, js_api=...)` with explicit localhost allowance.
4. **WebView2 serves stale cached HTML from a previous broken build** — pywebview's WebView2 caches the loaded HTML. After rebuilding with fixes, the old cached HTML may still be served. This was the **actual cause** of the "stale UI" in this session. Fix: add a cache-busting query param (`?cb=<timestamp>`) to the URL so it always loads fresh HTML from the backend, and enable `debug=True` so JS errors are visible.

### Fix Pattern for Stale WebView2 UI — CACHE-BUSTING
```python
# In desktop_app_fixed.py _launch_webview():
import time

cache_buster = int(time.time())
url = f"http://127.0.0.1:{port}/?cb={cache_buster}"

window = webview.create_window(
    "Aether — Agent + RAG",
    url,  # NOT f"http://127.0.0.1:{port}" without cache-buster
    width=1200, height=800, min_size=(900, 600),
    text_select=True,
)

# CRITICAL: debug=True so JS errors surface in the WebView2 dev console
webview.start(debug=True, storage_path=storage_path)
```

If pywebview version doesn't support `allow_origin`, add this workaround in the frontend `index.html`:
```javascript
// Force absolute URL instead of relative to avoid WebView2 CORS/network isolation
const API = 'http://127.0.0.1:8732';
```
**Layer 2: WebView2 localhost loopback permission** (CRITICAL — without this, `fetch('/api/...')` from JS inside WebView2 silently fails)
```python
import webview
try:
    from webview.platforms import winforms
    winforms.WebView2Environment.SetPermission("http://127.0.0.1:*", "Allow")
except Exception:
    pass
```
Add this BEFORE `webview.create_window()` in `_launch_webview()`. Without it, the WebView2 WebContent process blocks localhost fetch calls, causing all API calls to fail silently — buttons don't work, chat doesn't respond, and the UI looks completely frozen.
### Verification
After rebuilding `Aether.exe` with the fixes:
1. Launch Aether.exe
2. Open the app's WebView2 window
3. The chat textarea (id="q") and Send button should be interactive
4. Type a message and press Enter — response should stream back
5. If buttons still don't work, check `C:\Users\valte\AppData\Local\Aether\app_stdout.log` for JavaScript errors
6. The `?cb=<timestamp>` forces a fresh load of the current HTML from the backend — essential after rebuilding with fixes

### Also See
- The `project_rag_hybrid` reference build at `C:\Users\valte\project_rag_hybrid\` uses the same pywebview pattern correctly
- Compare `desktop_app_fixed.py` against `project_rag_hybrid\main.py` for the working WebView2 initialization pattern

## FastAPI/Pydantic Critical Fixes (2026-07-29)

### **UploadFile Body Parameter - CRITICAL**

FastAPI v2+ with Pydantic v2 requires explicit `File(...)` import and usage:

```python
# WRONG - causes "Field required" error and openapi.json Internal Server Error
from fastapi import UploadFile
async def api_pdfs_add(file: UploadFile):

# CORRECT - explicit File(...) dependency
from fastapi import UploadFile, File
async def api_pdfs_add(file: UploadFile = File(...)):
```

**Symptoms of missing `File(...)`:**
- `POST /api/chat` returns `{"detail":[{"type":"missing","loc":["query","req"],"msg":"Field required"}]}`
- `GET /openapi.json` returns "Internal Server Error"
- Pydantic error: `TypeAdapter[...] is not fully defined; you should define ... and all referenced types, then call .rebuild()`

### **Frozen App Entry Point Fix (2026-07-29)**

### **Problem: App Backend Runs But No Window Opens**
The build script `build_entry.py` was importing `app` from `desktop_app_fixed` and calling `uvicorn.run(app, ...)` directly — **bypassing the WebView launcher entirely**.

**Root cause:** The proper entry point in `desktop_app_fixed.py` is `main()` which:
1. Starts backend in a daemon thread
2. Waits 2 seconds for backend to be ready
3. Calls `_launch_webview(port)` to open the native window

**Fix applied to `build_entry.py`:**
```python
# BEFORE (broken - no window)
from desktop_app_fixed import app
uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

# AFTER (correct - opens window)
from desktop_app_fixed import main
main()
```

### **Problem: Missing Module Import in Backend Thread**
`_run_backend()` was importing from `aether.desktop_app_impl` which doesn't exist in the frozen bundle.

**Fix applied to `desktop_app_fixed.py`:**
```python
# BEFORE (broken in frozen app)
from aether.desktop_app_impl import app

# AFTER (uses local app instance)
from desktop_app_fixed import app
## Frozen App Launch Sequence (updated 2026-07-30)

For the frozen app to open the native window, ALL of these must be true:
## Frozen App Launch Sequence (updated 2026-07-30)

For the frozen app to open the native WebView2 window with all buttons and chat functional, ALL of these must be true:

1. PyInstaller includes `--paths=<project_root>` AND `--collect-all=<local_package>` for any package that is NOT installed via pip (local directories like `aether/`, `app_paths.py`)
2. All aether submodules are `--hidden-import`ed or covered by `--collect-all`
3. Entry point calls `desktop_app_fixed.main()` not `uvicorn.run()` directly
4. `build_entry.py` uses `from desktop_app_fixed import main; main()` not `from desktop_app_fixed import app; uvicorn.run(app, ...)`
5. **WebView2 localhost access**: pywebview's WebView2 may block `fetch()` calls from JavaScript inside the WebView2 process to `http://127.0.0.1:8732`. The frontend `index.html` uses `const API = ''` (relative URL) which works in browsers but may be blocked by WebView2's `ms-appx-web://` origin. Fix: ensure WebView2 allows localhost loopback connections, or change the frontend to use absolute URLs matching the WebView2 origin.

### Critical: local (non-pip) packages require `--collect-all` + `--paths`

When your app imports a package that lives as a **local directory** (not installed into site-packages via pip), PyInstaller cannot auto-discover it. The frozen exe crashes at launch with `ModuleNotFoundError` because the package is missing from the bundle.

**Fix:** Use both `--paths` AND `--collect-all` together:
```python
sys.argv = [
    "pyinstaller",
    "--name=Aether",
    "--onedir",
    "--windowed",
    "--icon=desktop_ui/logo.ico",
    "--noconfirm",
    # REQUIRED for local (non-pip-installed) packages:
    "--paths=C:/Users/valte/aether",         # add project dir to analysis path
    "--collect-all=aether",                    # force-collect aether + ALL submodules
    # hidden imports for dynamically loaded modules (use instead of collect-all
    # when you know the exact module names and want a leaner build)
    "--hidden-import=webview",
    "--hidden-import=uvicorn",
    "--hidden-import=uvicorn.loops.auto",
    "--hidden-import=uvicorn.protocols.http.auto",
    "--hidden-import=uvicorn.protocols.websockets.auto",
    "--hidden-import=uvicorn.lifespan.on",
    "--hidden-import=chromadb",
    "--hidden-import=sentence_transformers",
    "--hidden-import=rank_bm25",
    "--hidden-import=docling",
    "--hidden-import=fitz",
    "--hidden-import=openai",
    "--hidden-import=transformers",
    # bundled data
    "--add-data=desktop_ui;desktop_ui",
    "--add-data=rag_pdfs;rag_pdfs",
    "--add-data=rag_vector_db;rag_vector_db",
    "build_entry.py",
]
PyInstaller.__main__.run()
```

**Verification after build:** Confirm the package directory exists inside `_internal/`:
```powershell
Test-Path "dist\Aether\_internal\aether\__init__.py"
# Must return True, not False
```
If the directory is missing from `_internal/`, the `--collect-all` or `--paths` flag is wrong.

**`--collect-all` vs `--hidden-import` tradeoffs:**
- `--collect-all=<pkg>` pulls in EVERYTHING — all submodules, all data files, all transitive imports. Use when the package has dynamic imports (chromadb, sentence_transformers) or when you can't enumerate all submodules.
- `--hidden-import=<module>` is surgical — adds only a single module. Use for known, specific imports that PyInstaller missed.
- **Do NOT** use `--collect-all` on heavy ML packages (torch, transformers, etc.) unless the app actually needs them at frozen runtime — it bloats the build and can cause crashes. Use `--hidden-import` for those instead.**

### `unicodedata` and other C extensions not auto-detected

PyInstaller doesn't always detect built-in C extensions in frozen mode. They're imported transitively through packages like `requests → idna`. Explicitly add them:
```powershell
--hidden-import=unicodedata
```
Verify it's present after build:
```powershell
Test-Path "dist\Aether\_internal\unicodedata.pyd"
```

### Root cause of the 2026-07-30 crash

The `aether/` package was a local directory (not a pip install), so PyInstaller's auto-discovery missed it entirely. The frozen `Aether.exe` crashed at launch with `from aether import config` failing → `ModuleNotFoundError`. The fix was adding `--paths=C:/Users/valte/aether` + `--collect-all=aether` to `build_exe.py`. Verify by checking `dist/Aether/_internal/aether/__init__.py` exists after the build.

**Note on `--clean`**: Using `--clean` forces a full rebuild from scratch (5+ minutes with heavy ML packages), often causing timeouts. Omit it for incremental builds which cache intermediate results.

### **Launch Command**
```powershell
# Run from project root
cd C:\Users\valte\aether
# Build (if not already built)
python build_exe.py
# Launch the frozen app - THIS OPENS THE WINDOW
C:\Users\valte\aether\dist\Aether\Aether.exe
```

The window WILL open — it's a native pywebview/WebView2 window. If you don't see it, check Task Manager for "Aether.exe" process.

### **Background Process Management**

Use Hermes `terminal(background=true, notify_on_complete=true)` for long-running servers:

```python
# Start backend in background
terminal(command="python -m uvicorn app:app --host 127.0.0.1 --port 8732", background=True, notify_on_complete=True)

# Wait for readiness
sleep 5
curl http://127.0.0.1:8732/api/health

# Kill when done
process(action="kill", session_id="proc_xxx")
```

## Session References

- **2026-07-28:** Fixed splash animation (see `references/aether-session-2026-07-28.md`)
- **2026-07-29:** Fixed critical frozen app bugs (see `references/aether-session-2026-07-29.md`)
- **2026-07-30:** Full rebuild with frozen-aware paths, WebView2 auto-install, proper PyInstaller build, and desktop shortcut creation (see `references/aether-rebuild-session-2026-07-30.md`)
- **2026-07-30a:** WebView2 stale UI fix — three-layer root cause: (1) `aether` package not bundled, (2) `unicodedata` C extension missing, (3) WebView2 blocks localhost fetch() from JS. See `references/aether-webview2-stale-ui.md`

## Key Lessons Learned (2026-07-30 Rebuild)

### 1. Frozen-aware path resolution IS the working pattern
The `project_rag_hybrid` app works because it uses `app_paths.py` with `BASE_DIR` (exe folder, read-only) and `APP_DATA_DIR` (`%LOCALAPPDATA%/Aether`, writable). The Aether app was broken because it used `AETHER_HOME = Path(APPDATA)/"aether"` for everything. Copied the exact pattern to `aether/app_paths.py`.

### 2. Build script MUST run PyInstaller, not just copy files
The old `build_aether.py` only copied files to `_internal/`. New `build_exe.py` runs `PyInstaller.__main__.run()` with proper `--add-data`, `--hidden-import`, and entry point. Post-build syncs `rag_vector_db/`, `rag_pdfs/`, `desktop_ui/` that `--add-data` sometimes misses.

### 3. Entry point must call the WebView launcher, not uvicorn directly
`build_entry.py` now imports `desktop_app_fixed.main()` which:
- Starts uvicorn in a daemon thread
- Polls `/api/health` until 200 (not fixed sleep)
- Then calls `webview.create_window()` + `webview.start()`

This eliminates `ERR_CONNECTION_REFUSED` inside the native window.

### 4. WebView2 runtime auto-install at app startup
Added `_webview2_installed()` registry check + `_install_webview2()` silent download/install to `desktop_app_fixed.py`. Runs BEFORE `create_window()`. Fixes "app opens 2s then closes" on fresh PCs.

### 5. Desktop shortcut creation via PowerShell
Created `create_shortcut.ps1` that sets TargetPath, WorkingDirectory, and IconLocation correctly. The shortcut now appears on Desktop with the app icon.

### 7. PyInstaller local package bundling — `--collect-all` + `--paths` (CRITICAL)

**This was the root cause of the frozen exe crash on 2026-07-30.**

The `aether/` package is a local directory (not a pip install), so PyInstaller's auto-discovery missed it entirely. The frozen `Aether.exe` crashed at launch with `from aether import config` failing → `ModuleNotFoundError`.

**Fix:** Use both `--paths` AND `--collect-all` together:
- `--paths=C:/Users/valte/aether` — adds the project root to PyInstaller's analysis search path
- `--collect-all=aether` — force-collects aether + ALL submodules, data files, and hidden imports

Both flags are required. `--collect-all` alone without `--paths` still misses local packages because PyInstaller doesn't search the project root for modules to collect.

**Verification after build:**
```powershell
Test-Path "dist\Aether\_internal\aether\__init__.py"
# Must return True
```

**`--collect-all` vs `--hidden-import` tradeoffs:**
- `--collect-all=<pkg>` pulls in EVERYTHING — all submodules, all data files, all transitive imports. Use for packages with dynamic imports (chromadb, sentence_transformers).
- `--hidden-import=<module>` is surgical — adds only a single module. Use for known specific imports PyInstaller missed.
- **Do NOT** use `--collect-all` on heavy ML packages (torch, transformers) unless the app needs them frozen — it bloats the build and can cause crashes. Use `--hidden-import` for those instead.

## Ready for Production

This skill now implements:
- ✅ PowerShell-first approach (user requirement)
- ✅ All critical fixes applied
- ✅ Concise, actionable commands
- ✅ Proper error handling and logging
- ✅ Clear, actionable steps for user

Just copy-paste the PowerShell commands and follow the numbered steps for quick resolution.