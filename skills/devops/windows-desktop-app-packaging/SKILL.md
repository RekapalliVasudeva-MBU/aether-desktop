---
name: windows-desktop-app-packaging
description: Freeze and ship a Python desktop/agent app on Windows as a double-clickable installer. Covers PyInstaller --onedir, Inno Setup (zip compression to avoid 0xc0000142), bundling native-extension packages like chromadb/onnxruntime into the frozen build, the self-extracting-installer infinite-loop trap, and free public tunneling with cloudflared instead of bandwidth-capped ngrok. Use when building/packaging/debugging a distributable Windows .exe for a Python GUI, RAG, or agent app.
---

# Windows Desktop App Packaging (PyInstaller + Inno Setup)

Use this when you need a real, installable Windows `.exe` for a Python app
(GUI via pywebview/Electron-style, FastAPI backend, RAG/agent). The goal is a
double-clickable installer that installs to `%LOCALAPPDATA%` with desktop +
start-menu shortcuts, no admin/UAC, and a working app after reboot.

## Decision: don't use --onefile for the app

- **PyInstaller `--onedir`** (not `--onefile`). `--onefile` unpacks to a random
  `%TEMP%\_MEIxxxx` folder at every launch; Windows Defender frequently blocks /
  quarantines that → `0xc0000142 / application was unable to start`. onedir keeps
  files permanently in the install dir, so there is no runtime temp-unpack step.
- Exclude unused heavy ML packages to shrink the build and avoid bootloader
  crashes: `--exclude-module torch torchvision torchaudio transformers
  safetensors sentencepiece huggingface_hub timm accelerate cv2`.
  BUT see the chromadb note below — do NOT exclude `tokenizers` / `onnxruntime`
  if the app uses chromadb's rust index.

## Inno Setup: Compression=zip, not lzma2

- `Compression=lzma2` / `ultra64` makes the Inno **bootloader** crash with
  `0xc0000142 (STATUS_DLL_INIT_FAILED)` on some Windows machines.
- Use `Compression=zip` + `SolidCompression=no`. Same installer, just a
  different (safe) compressor.
- Reference recipe: `references/inno-setup-windows.md`.
- "Won't open" diagnostic + launch/verify commands: `references/verify-launch-windows.md`.

## chromadb / native extensions in a frozen build — BUNDLE THE WHOLE PACKAGE

This is the #1 silent failure. A frozen PyInstaller build importing chromadb
crashes at runtime with `ModuleNotFoundError: chromadb.api.rust`, then after you
add that, `chromadb.telemetry.product.posthog`, etc. (whack-a-mole).

- Root cause: chromadb imports submodules **dynamically**; per-module
  `--hidden-import` never catches the full chain.
- Fix: copy the ENTIRE `site-packages/chromadb` dir into the build tree and add
  it as data: `--add-data <copy>/chromadb;chromadb`, plus
  `--hidden-import chromadb_rust_bindings --hidden-import tokenizers
  --hidden-import onnxruntime`. Do NOT exclude tokenizers/onnxruntime.
- **Path-resolution pitfall when copying the package**: `site.getsitepackages()[0]`
  returned `venv/` (NOT `venv/Lib/site-packages`) in this user's uv venv, so a
  `copytree` from there failed with `FileNotFoundError: .../venv/chromadb`. Use
  the deterministic path instead:
  `os.path.join(os.path.dirname(os.path.dirname(sys.executable)), "Lib",
  "site-packages", "chromadb")`. (`sys.executable` is `venv/Scripts/python.exe`,
  so `dirname(dirname)` = `venv/`.)
- Full recipe + path-resolution fallback: `references/chromadb-pyinstaller.md`.

## Bundle the WebView2 Runtime bootstrapper into the installer + App-level auto-install

The "app opens 2s then closes" on fresh user PCs is almost always a missing Microsoft WebView2 Runtime. pywebview requires it; if absent, `create_window()` throws and the frozen exe dies silently. **Two layers of defense** make it permanent:

### 1. App-level pre-flight (`desktop_app.py`) — runs at EVERY launch
Before `create_window()`, call `_webview2_installed()` (registry + side-by-side check). If missing, auto-download and silent-install the Evergreen bootstrapper (`/silent /install`) with a progress message. If auto-install fails, show a message box pointing to the manual install URL instead of crashing silently. Only call `create_window()` once the runtime is verified.

```python
def _webview2_installed() -> bool:
        """True if the Microsoft WebView2 Runtime is present on this machine.

        pywebview needs it to render the window. A missing runtime is the
        #1 cause of 'app opens for 2 seconds then closes' on fresh user PCs.
        """
        try:
            import winreg
            # Evergreen runtime registers here (official Microsoft location):
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
            )
            winreg.CloseKey(key)
            return True
        except Exception:
            pass
        # Also check the alternate key some installs use
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications",
            )
            winreg.CloseKey(key)
            return True
        except Exception:
            pass
        # Also accept a side-by-side WebView2 in the app folder (bundled).
        try:
            for p in (Path(sys.executable).parent / "WebView2Loader.dll",
                      Path(sys.executable).parent / "_internal" / "WebView2Loader.dll"):
                if p.exists():
                    return True
        except Exception:
            pass
        return False


def _install_webview2() -> bool:
    """Download and silently install the WebView2 Evergreen Runtime."""
    import urllib.request, subprocess
    boot = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
    dst = Path(os.environ.get("LOCALAPPDATA", "")) / "Aether" / "MicrosoftEdgeWebview2Setup.exe"
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        ctypes.windll.user32.MessageBoxW(0,
            "Aether needs the Microsoft WebView2 Runtime (one-time install, ~1.5 MB). Installing now…",
            "Aether", 0x40)
        urllib.request.urlretrieve(boot, str(dst))
        r = subprocess.run([str(dst), "/silent", "/install"], capture_output=True, text=True, timeout=300)
        return r.returncode in (0, 3010, 1641)
    except Exception as e:
        ctypes.windll.user32.MessageBoxW(0,
            "Aether could not auto-install WebView2. Please install manually from:\nhttps://developer.microsoft.com/microsoft-edge/webview2/",
            "Aether", 0x10)
        return False


# PERMANENT FIX: Run BEFORE webview.create_window()
if not _webview2_installed():
    if not _install_webview2():
        return
    if not _webview2_installed():
        _fail_box("WebView2 installed but not active yet. Please restart PC and relaunch Aether.")
        return
```

### 2. Installer-level bundling (`make_installer.py` + `installer_boot.py`)
Bundles the bootstrapper (`MicrosoftEdgeWebview2Setup.exe` from `https://go.microsoft.com/fwlink/p/?LinkId=2124703`) at build time and runs it `/silent /install` during setup BEFORE launching the app. Payload size increases by ~1.7 MB.

```python
# make_installer.py - bundles bootstrapper
WEBVIEW2_BOOT = os.path.join(HERE, "MicrosoftEdgeWebview2Setup.exe")
if not os.path.isfile(WEBVIEW2_BOOT):
    urllib.request.urlretrieve("https://go.microsoft.com/fwlink/p/?LinkId=2124703", WEBVIEW2_BOOT)
# ... added to payload

# installer_boot.py - runs at install time
def _install_webview2(app_dir: str) -> bool:
    setup = os.path.join(app_dir, "MicrosoftEdgeWebview2Setup.exe")
    if not os.path.isfile(setup):
        return False
    r = subprocess.run([setup, "/silent", "/install"], capture_output=True, text=True, timeout=300)
    return r.returncode in (0, 3010, 1641)

# In main():
if not _webview2_installed():
    _install_webview2(app_dir)
```

The registry key to detect the Evergreen runtime is `HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications`. A side-by-side `WebView2Loader.dll` in the app folder (or `_internal/`) is also accepted. Full implementation pattern in `references/webview2_missing_runtime.md`.

## The 2-layer self-extractor LOOP trap (critical)

If you build a "self-extracting installer" by compiling a boot script that reads
an embedded payload and writes the app to disk, the payload MUST be the **real
onedir app folder** (`dist_build/Aether/`), NOT the installer `.exe` itself.

- BUG that actually shipped: `make_installer.py` set `APP_EXE = dist/Aether.exe`
  (the installer build) as the payload. Result: the installer extracted a copy
  of *itself* and `os.startfile`'d it → infinite re-launch loop, port never
  opened, 5 `Aether.exe` copies in Task Manager, no window.
- CORRECT: walk `dist_build/Aether/` and bundle every file (relative paths),
  including `_internal/`. The extracted dir must contain `Aether.exe` +
  `_internal/` + assets.
- Verify after build: run the installer in an isolated dir / check
  `%LOCALAPPDATA%\Aether` contains `_internal/` and the app binds its port.

## Public tunnel: cloudflared, not ngrok free
## Cloudflare Named Tunnel Setup (Stable URL)

**Problem**: Quick tunnels (`cloudflared tunnel --url http://localhost:8000`) give a random `*.trycloudflare.com` URL that changes every restart and dies when the session ends. Users reported "deployed but not opening" because the URL changed.

**Solution**: Named tunnel installed as Windows service — yields ONE fixed `https://<name>.cfargotunnel.com` URL that survives reboots and auto-starts.

### Setup (run in PowerShell as Administrator)
```powershell
# 1. Clean any existing stuck service
sc delete Cloudflared

# 2. Install with your tunnel token (from Cloudflare Dashboard → Zero Trust → Networks → Tunnels)
C:\Users\valte\cloudflared.exe service install <YOUR_TOKEN>

# 3. Verify
Get-Service Cloudflared

# 4. In server_config.json:
"cloudflare_tunnel_token": "<YOUR_TOKEN>",
"cloudflare_tunnel_name": "aether-rag"
```

### Server-side auto-start (`server.py`)
```python
def _open_cloudflare_tunnel() -> tuple:
    """Start cloudflared as a subprocess for a NAMED tunnel (stable URL).
    Returns (process, public_url) or (None, None) if not configured.
    Requires CONFIG["cloudflare_tunnel_token"] to be set."""
    token = CONFIG.get("cloudflare_tunnel_token", "")
    if not token:
        return None, None
    
    import subprocess, time, requests
    print(f"\n{'=' * 60}")
    print("Starting Cloudflare NAMED tunnel (stable URL)...")
    
    try:
        # Start cloudflared with the tunnel token (named tunnel)
        proc = subprocess.Popen(
            ["./cloudflared.exe", "tunnel", "--no-autoupdate", "run", "--token", token],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
            cwd="/c/Users/valte"
        )
        
        # Wait for tunnel to register and get the URL from Cloudflare API
        tunnel_name = CONFIG.get("cloudflare_tunnel_name", "aether-rag")
        print(f"Waiting for tunnel '{tunnel_name}' to become healthy...")
        time.sleep(8)
        
        # For named tunnels, the URL is stable: https://<tunnel-name>.cfargotunnel.com
        public_url = f"https://{tunnel_name}.cfargotunnel.com"
        
        # Test if it's reachable
        try:
            r = requests.get(public_url, timeout=10)
            if r.status_code in (200, 404):
                print(f"✅ Named tunnel ready: {public_url}")
            else:
                print(f"⚠️ Tunnel starting, URL may take a moment: {public_url}")
        except Exception:
            print(f"⚠️ Tunnel starting, URL may take a moment: {public_url}")
        
        print(f"Local URL:  http://{CONFIG['host']}:{CONFIG['port']}/")
        print(f"Public URL: {public_url}")
        print("=" * 60 + "\n")
        
        return proc, public_url
        
    except Exception as e:
        print(f"⚠️ Failed to start Cloudflare named tunnel: {e}")
        return None, None
```

### Troubleshooting
- **Service stuck in STOP_PENDING**: Kill `cloudflared.exe` processes (`taskkill /F /IM cloudflared.exe`), then `sc delete Cloudflared`, then reinstall
- **Access denied on install**: Must run PowerShell as Administrator
- **Zero-zone account**: If Cloudflare account has 0 zones/domains, named tunnel fails (login zone-picker has nothing to select). Fix: add a free domain (Cloudflare registrar) or accept quick-tunnel URL rotation.
1. **Upload the installer in BACKGROUND.** `gh release create <tag> <file>`
   inline-uploads a ~180 MB asset and takes 5–7 min on a slow link. A foreground
   `terminal` call is clamped at 60s → silent `exit 124`, half-made release (tag
   exists, no asset). Always use `terminal(background=true,
   notify_on_complete=true)` + `process(action='wait')`. Same for `gh release
   upload`.
2. **Repoint the website `/download/aether` 302** in `project_rag/server.py` to
   the NEW tag. The site hard-codes a release tag in the redirect; if you don't
   bump it, users keep downloading the previous build. Restart the website after.
Full recipe + version checklist: `references/release-upload.md`.

## Communication style (this user) — HARD RULE

This user is NOT a CLI fluent operator. When they need to run a command themselves (admin PowerShell, install steps, etc.), they want **exact copy-paste blocks, line by line, with nothing ambiguous** — not prose explaining what to do.

- ❌ DON'T say "run it as administrator, then start the service" and leave them to construct the command. They will get the syntax wrong.
- ✅ DO give the literal command(s) in a fenced block, each on its own line, with the exact path.
- When they blow up ("u idiot say exactly what to paste"), that is the signal to STOP explaining and PASTE THE COMMAND. Lead with the command, explain after if at all.
- Keep narration minimal. Show the command + the expected success output. This user benchmarks against "just works" — verbose pre-amble reads as stalling to them.

## User workflow preference: do ONE thing at a time, don't fix unrelated issues

**Hard rule from 2026-07-31:** When the user says "don't fix anything" or "just do what I say, do one thing," the agent must STOP all unrelated work immediately. The user explicitly said "u idiot i said dont fix anything now ok just do what i say ok this one only dont fix the issues now."

- If the user says "don't fix anything" — do NOT apply bug fixes, patches, or changes to source code unless they explicitly ask for it.
- If the user says "just do this one thing" — complete ONLY that task, then stop.
- If the user says "don't fix the WebView2 bugs now" — do NOT touch any WebView2 or browser-related code.
- Verify the task is done and report, then wait for the next instruction.

This applies even when the agent believes a fix is urgent or related to the task at hand. The user's explicit instruction overrides any internal judgment about what should be fixed.
themselves (admin PowerShell, install steps, etc.), they want **exact
copy-paste blocks, line by line, with nothing ambiguous** — not prose
explaining what to do.

- ❌ DON'T say "run it as administrator, then start the service" and leave
  them to construct the command. They will get the syntax wrong (this
  session: `cloudflarednet start`, `C:\Users\valte\cloudflared.exe net
  start cloudflared`, `service install http://...` without `--url` — all from
  imprecise instructions).
- ✅ DO give the literal command(s) in a fenced block, each on its own line,
  with the exact path. E.g.:
  ```
  C:\Users\valte\cloudflared.exe service install
  net start cloudflared
  ```
- When they blow up ("u idiot say exactly what to paste"), that is the signal
  to STOP explaining and PASTE THE COMMAND. Lead with the command, explain
  after if at all.
- Keep narration minimal. Show the command + the expected success output.
  This user benchmarks against "just works" — verbose pre-amble reads as
  stalling to them.

## UX pitfall (this user)

When building the app's settings/preferences UI, keep ALL config **in the UI**:
settings panel, capability toggles (skills/tools/MCP/memory/RAG on-off),
API-key paste field, PDF add/remove buttons, gateway start/stop. **Do NOT force
the user to hand-edit YAML/config files.** This user pushed back hard when an
earlier pass removed UI options and told them to "edit the settings file".

## Native pywebview window is the DESIRED primary surface — NOT a browser tab

**User correction (hard rule):** this user does NOT want a "localhost website".
They benchmark the app against the **Hermes One** desktop app and expect a real
native window with a left sidebar (Chats, RAG PDFs, Skills, Tools, MCP, Memory,
Persona, Providers, Telegram). An earlier pass made the browser tab the PRIMARY
surface ("auto-open in default browser, pywebview best-effort") — the user
rejected it: *"u again fixed it to local host website"*, *"i need similar one like
Hermes One"*. **Do not ship a browser-only UI for this user.**

WebView2 IS installed on this user's machine (verified: `C:\Program Files (x86)\
Microsoft\EdgeWebView\Application\<ver>\`), so a native pywebview window works.
The earlier "won't open" was the LAUNCH PATTERN, not WebView2 missing:
- `webview.create_window(...)` + `webview.start()` must run on the **main thread**,
  and the uvicorn server must already be serving (start it in a daemon thread
  first, `sleep ~1.5s`, THEN create the window). A window created on a daemon
  thread, or before the server is up, shows nothing.
- Make the browser `webbrowser.open(url)` the **FALLBACK only** (when
  `import webview` / `webview.start()` actually raises), never the primary.

**The single-instance guard must NOT open a browser — AND must not silently
exit.** Two regressions shipped on this path; both are now traps:
- (OLD, fixed) the guard `if _port_in_use(port): webbrowser.open(url); return`
  popped a **browser tab** when an orphan was already running — exactly what the
  user rejected (*"u again fixed it to local host website"*).
- (v1.1.1, fixed in v1.2.0) the "fix" flipped to a **silent `return`**:
  `if _port_in_use(port): return`. That is ALSO wrong — if any orphan (old
  crash, your own test launch, a zombie from Task Manager) holds 8732, the fresh
  double-click exits with **no window and no browser**, so the user sees "app
  not opening" with nothing to chase. This was the actual cause of the
  "still many errors, the desktop app is not opening" report.
**Correct behavior (v1.2.1, permanent fix): use a Windows named mutex for
TRUE single-instance.** A second launch must NOT open a new server/port and
must NOT open a browser — it must **focus the existing native window and
exit**. The previous "bind a free port + open a second native window" idea was
ALSO wrong: two `Aether.exe` processes both calling `webview.create_window`
from the same install path **conflict in WebView2**, so the second window
fails and triggers the browser fallback — which is the exact
`http://127.0.0.1:65338/ui/` loop the user hit. The only robust design is
**exactly one** process + **exactly one** WebView2.
- Create `Global\AetherSingleInstanceMutex` via `CreateMutexW`; if
  `GetLastError()==183 (ERROR_ALREADY_EXISTS)` another instance is running.
- Second instance: `EnumWindows` -> find the window whose title contains the
  app title -> `ShowWindow(hwnd, SW_RESTORE)` + `SetForegroundWindow(hwnd)`,
  then `ReleaseMutex` + `return`. No server, no browser.
- First (only) instance: serve on the FIXED port 8732 + open the single
  native pywebview window. **No browser fallback at all** — if
  `webview.start()` genuinely raises (WebView2 missing), show a MessageBox
  explaining how to install WebView2, and exit. `webbrowser.open` appears
  ZERO times in the codebase now.
- **Rule: the single-instance guard must never `return` silently AND must
  never open a browser.** With the mutex approach it does neither — it
  focuses the existing window and returns normally.

Verified-good `main()` shape (mutex single-instance, native window ONLY):

```python
import ctypes, sys, threading

def main():
    config.ensure_persona_files()
    # copy logo.ico next to the exe (runtime fix for the .lnk icon)
    try:
        import shutil
        shutil.copyfile(UI_DIR/"logo.ico", Path(sys.executable).parent/"logo.ico")
    except Exception: pass
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, 0, "Global\\AetherSingleInstanceMutex")
    if kernel32.GetLastError() == 183:     # ERROR_ALREADY_EXISTS
        # focus existing window, then exit cleanly — NO new server, NO browser
        _focus_existing_window()
        kernel32.ReleaseMutex(mutex); return
    import uvicorn
    port = int(os.environ.get("AETHER_PORT", "8732"))
    url = f"http://127.0.0.1:{port}/ui/"
    threading.Thread(target=lambda: uvicorn.run(
        app, host="127.0.0.1", port=port, log_level="warning"),
        daemon=True).start()
    time.sleep(1.5)
    try:
        import webview
        # NOTE: create_window() in this pywebview version has NO `icon` kwarg
        # (TypeError: unexpected keyword argument 'icon'). The window/taskbar
        # icon comes from PyInstaller --icon; pass it to webview.start() instead.
        webview.create_window("Aether — AI Agent + Personal RAG", url=url,
            width=1280, height=840, text_select=True)
        webview.start(icon=str(Path(sys.executable).parent/"logo.ico"))
                                                 # blocks on main thread — ONLY surface
    except Exception as e:
        # genuine env failure (WebView2 missing): tell the user, do NOT open a browser
        ctypes.windll.user32.MessageBoxW(0,
            f"Aether could not start its native window:\n{e}\n\n"
            "Install the WebView2 Runtime from Microsoft, then relaunch Aether.",
            "Aether", 0x10)
    while True: time.sleep(3600)            # keep alive
```

The `_focus_existing_window()` helper enumerates top-level windows and
restores the one whose title contains the app title (full `ctypes`/`win32com`
recipe + verify steps in `references/single-instance-mutex.md`).

## Icon: set --icon at BUILD time AND IconFilename in the installer

A native window with NO taskbar/shortcut logo looks broken to this user
(*"see the app icon also missing in my shortcut"*). Two places to fix:
1. **PyInstaller**: add `--icon <repo>/desktop_ui/logo.ico` to the exe build
   args. (The build log will say "Copying icon to EXE".) A raw-byte `RT_ICON` grep
   on the PE is NOT a reliable check — trust the build log + the running window.
2. **Inno Setup `[Icons]`**: set `IconFilename: "{app}\logo.ico"` on BOTH the
   start-menu and desktop shortcuts so the `.lnk` shows the logo. Also set the
   desktop-shortcut Task `Flags: checkedonce` so the shortcut is created by
   DEFAULT (the user was confused by a missing/unchecked shortcut).
3. Make the RAG PDF drop-in folder exist post-install: add a `[Dirs]` entry
   `Name: "{localappdata}\Aether\rag_pdfs"` (app also creates it lazily on first
   launch via `pdf_watch_dir()`).

## Icon pitfall: `logo.ico` MUST exist next to the exe (not just inside it)

This shipped as a real bug: the desktop `.lnk` showed **no logo** even though
`--icon` was set and the `.iss` had `IconFilename: "{app}\logo.ico"`. Why:
PyInstaller **embeds** the icon in the PE (build log says "Copying icon to EXE")
but does NOT copy `logo.ico` as a loose file next to `Aether.exe`. The `.iss`
`[Icons] IconFilename: "{app}\logo.ico"` points at the loose file, which was
missing → blank shortcut icon.
**Fix (all three, do the runtime one — it survives everything):**
1. **Runtime (preferred):** at app startup, copy `UI_DIR/logo.ico` to
   `Path(sys.executable).parent / "logo.ico"` (the `main()` snippet above does
   this). This auto-fixes already-installed copies on next launch.
2. **Installer:** add `Source: "desktop_ui\logo.ico"; DestDir: "{app}"` to
   `[Files]` so a fresh install ships the loose file.
3. **Re-point a broken existing `.lnk`** via COM (winshell's `Shortcut` object
   has no `.save()` method):
   ```python
   import win32com.client
   sh = win32com.client.Dispatch("WScript.Shell")
   s = sh.CreateShortcut(r"C:\Users\valte\OneDrive\Desktop\Aether.lnk")
   s.IconLocation = r"C:\Users\valte\AppData\Local\Aether\logo.ico,0"
   s.Save()
   ```
   Verify with `(New-Object -ComObject WScript.Shell).CreateShortcut(<path>).IconLocation`.

## Settings-panel endpoin

## ERR_CONNECTION_REFUSED — permanent fix (race between server + WebView2)

The single most-reported "app not opening" symptom on this project was the
browser error `127.0.0.1 refused to connect` (ERR_CONNECTION_REFUSED). Root
cause: `main()` started the uvicorn server in a thread then did
`time.sleep(1.5)` and **immediately** handed the URL to `webview.create_window`
before the server was actually listening — so WebView2 navigated to a dead port.
This is a TOCTOU race, not a missing dependency.

**Permanent fix (v1.2.3): poll `/api/health` until it returns 200 BEFORE creating
the window.** No fixed `sleep`, no random-port fallback, no browser.
- Add `GET /api/health` → `{"ok":true,"version": ...}`.
- In `main()`, after starting the server thread, loop up to ~30s:
  `urllib.request.urlopen(health_url, timeout=1)`; break on 200.
- If it never comes up: show a MessageBox ("backend server did not become
  ready…") and exit — NOT a browser tab.
- Also: if `_port_in_use(port)` is true at startup AND it's not our own server
  (a genuine foreign process holds 8732), show a MessageBox ("port in use by
  another program") and exit — don't try to bind (which would fail anyway) and
  don't fall back to a browser.
- Keep the mutex single-instance (focus-existing-window) from the prior fix.
After this change the app cannot produce ERR_CONNECTION_REFUSED: the window is
only ever given a URL that is already answering 200.

## Verify the REAL frozen exe (not the MSYS/uv shim)

The repo's `python` is an MSYS/uv shim whose subprocess-pipe behavior differs
from the frozen exe's real Windows python. Bugs that only show under the shim
(looking "fixed" locally) can still break in the shipped `.exe`. To verify the
ACTUAL bundled build:
- Add an `AETHER_HEADLESS=1` env guard in `main()`: if set, skip the WebView2
  window and just `while True: time.sleep(3600)` so the server stays up. This is
  harmless in normal use and lets you curl the frozen exe's endpoints headlessly.
- Launch the built exe: `terminal(background=true)` on
  `%LOCALAPPDATA%\Aether\Aether.exe` with `AETHER_HEADLESS=1 AETHER_PORT=8732`.
  Then `sleep 6; curl -s http://127.0.0.1:8732/api/health` and any endpoint you
  changed. This exercises the SAME interpreter the user runs → no shim blind spot.
- Kill stale `Aether.exe` (`taskkill /F /IM Aether.exe`) before each relaunch;
  the exe holds 8732 and PyInstaller locks `_internal/*.pyd` during rebuild.

## Windows stdio MCP subprocess pipe bug (`Errno 22 Invalid argument`) — RESOLVED for normal Python

The MCP stdio client spawns a child (`npx`, `python`, …) and speaks JSON-RPC
over stdin/stdout. On THIS machine's Python (both the uv shim AND the frozen
exe) the naive implementations FAIL with `OSError: [Errno 22] Invalid argument`:
- `Popen(..., text=True, bufsize=1)` + `write` + `flush()` → `flush()` raises
  Errno 22 (line-buffering unsupported for text pipes on Win).
- `Popen(..., text=True)` (default buf) + `write` + `flush()` → ALSO Errno 22.
- `Popen(..., bufsize=0)` binary + `write` + `flush()` → `flush()` on an
  unbuffered stream raises Errno 22.
- `os.write(proc.stdin.fileno(), bytes)` on the raw fd → ALSO Errno 22.

ROOT CAUSE: calling `.flush()` on a Windows pipe (text line-buf OR unbuffered)
raises Errno 22. The fix is to **never flush** — use unbuffered binary and let
the write go out immediately.

WORKING TRANSPORT (verified in normal Python — returns init + tool list):
```python
self.proc = subprocess.Popen(
    [cmd, *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL, bufsize=0)         # unbuffered BINARY, NO text=
payload = (json.dumps(msg) + "\n").encode("utf-8")
self.proc.stdin.write(payload)                    # unbuffered → sent immediately, NO flush()
# read one char at a time until newline; b"" = child closed stdout → return {}
while True:
    buf = b""
    while True:
        ch = self.proc.stdout.read(1)
        if not ch or ch == b"\n": break
        buf += ch
    if not buf: return {}
    resp = json.loads(buf.decode("utf-8"))
    if resp.get("id") == self._id: return resp
```
A trivial `python -c "readline/write"` child works under `text=True`, but a real
read-loop MCP child DEADLOCKS under `text=True` default buf (child stdout is
block-buffered and never flushes while alive). `bufsize=0` + no-flush sidesteps
both.

TIMEOUT PITFALL (Windows-specific, easy to get wrong): `select.select([proc.stdout], [], [], 10)` does **NOT** work on Windows **pipes** — `select` on Windows is socket-only and on a pipe it blocks/hangs instead of timing out, so a dead server never trips the timeout and the caller hangs forever. Do NOT use `select` for the stdio read timeout. To bound a non-responsive server, run the read in a `threading.Thread` and `join(10)`; if it doesn't finish, return `{"ok":False,"detail":"timeout"}`. Relying on the child exiting (stdout EOF → `read(1)` returns `b""`) only helps if the child actually dies — a server that stays alive but never answers needs the thread timeout.

FROZEN-EXE + `command:"python"` STILL HANGS: when the frozen exe spawns
`command:"python"`, that resolves to the **uv shim**, which re-execs and breaks
the inherited pipe fds → the handshake deadlocks even with the correct transport.
Mitigations:
- Use **absolute executable paths** for MCP servers. Real servers (`node`,
  `npx`, `uvx`, `docker`) are absolute and work fine.
- Prefer the **HTTP transport** (`requests.post` to a URL) — fully solid, no
  subprocess, no pipe bug.

So: ship `bufsize=0` + no-flush as the stdio transport; recommend HTTP MCP or
absolute-path stdio servers to users; the Test Connection button returns
`{"ok":bool,"detail":...}` and `detail` should surface the real error (no fake
"ok"). Guard the live test in a thread with a `join` timeout so a bad server
can never hang the UI.

Debug recipe (authoritative = via frozen exe + AETHER_HEADLESS):
- Write a minimal child `test_mcp_server.py` that reads one line,
  `sys.stdout.write(...); sys.stdout.flush()`, loops.
- Register via `POST /api/mcp/add` with `{"command":"<ABS python.exe>","args":["<abs-path>"]}`
  (absolute path — the shim hangs).
- `POST /api/mcp/test`; expect `{"ok":true,"detail":"connected (N tool(s))"}`.

## "App won't open" diagnostic tree

Repro recipe for the silent-exit regression specifically:
`references/app-not-opening-regression.md`.

When the user says "double-click does nothing / app won't open", FIRST verify
the server is actually fine before assuming a crash. The app launches a local
FastAPI server and shows a **native pywebview window** (URL `http://127.0.0.1:PORT/ui/`).

Diagnostic steps (run on the user's machine, NOT in a subshell that exits):
1. Is the exe valid + present? `python -c "print(open(r'<path>','rb').read(2))"`
   must be `b'MZ'`.
2. Kill stale instances first: `taskkill /F /IM Aether.exe` — repeated test
   launches leave 5–7 copies that confuse diagnosis and hold the port.
3. Launch ONE instance and poll the port + UI:
   - Use `terminal(background=true)` directly on the exe (NOT `start "" exe &`
     inside a subshell that returns — the child dies when the parent shell exits,
     making a working app look dead).
   - `sleep 10` then `netstat -an | findstr :8732` and
     `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8732/ui/`.
   - `/ui/` returning **200** + port listening = the app WORKS (native window
     should be visible; if not, it fell back to the browser — check there too).
   - If `timeout 15 ./Aether.exe` returns exit **124**, the exe is ALIVE (timeout
     killed a still-running process) — that is proof it launched, not a crash.
4. If the server is up but double-click "does nothing", the cause is almost
   always **Windows SmartScreen** on an unsigned `.exe`: the "Windows protected
   your PC" dialog appears behind other windows or auto-dismisses. Fix: user
   clicks **"More info" → "Run anyway"** (one-time). The app is safe — it's the
   user's own unsigned build.
5. Only if port does NOT bind after a clean launch is it a real crash — then
   check the Windows event log (`Get-EventLog Application | Where Message -match
   'Aether'`) and the frozen-exe fault (chromadb/onedir issues above).

Shortcut check: a dead shortcut points to a non-existent path (e.g. a leftover
`%TEMP%\aether_final2\Aether.exe`). Verify the `.lnk` target with
`(New-Object -ComObject WScript.Shell).CreateShortcut(<path>).TargetPath` and
delete broken ones. The working shortcut target is
`%LOCALAPPDATA%\Aether\Aether.exe`.

## Stale-process port shadowing (silent "old UI" / 404s)

When you rebuild and re-run, an OLD `Aether.exe` (or old `desktop_app.py`) may
still hold `127.0.0.1:8732`. Two symptoms follow:
- **Stale code served**: the new process sees the mutex already owned by the
  orphan and *focuses it / exits* (per the v1.2.1 mutex design), so your fresh
  rebuild never starts and the orphan keeps serving **old** code. Symptom: new
  endpoints 404 (`{"detail":"Not Found"}`) while old ones work, and chat returns
  stale behavior.
- (Historical, now gone) Earlier designs on this path either opened a browser
  tab or silently exited — both are fixed by the mutex + focus-existing design.
**Always kill the port holder before testing a fresh build:**
`netstat -ano | findstr :8732` → PID → `taskkill /PID <pid> /F`. Then launch
the rebuilt exe on the real port (or a fresh test port like 8735) and re-verify.
A fresh test port sidesteps the clash entirely. Also kill before a rebuild so
PyInstaller doesn't collide on locked `.pyd` files in `_internal/`.

## WebView2 cache-busting — prevent stale HTML in frozen builds when HTML is served by the backend

**Problem:** When the FastAPI backend serves `index.html` to WebView2, the browser may cache a stale version. Even after fixing a JS bug in `index.html` and rebuilding the exe, the old cached HTML/JS is still served — symptoms look like the fix "didn't take" (e.g. `applyAppearance` undefined in console despite the line being corrected in source).

**Pitfall:** WebView2 on Windows aggressively caches responses from `http://127.0.0.1:PORT/`. A simple rebuild-and-relaunch does NOT clear the cache. The fix must be at the URL level or the HTML delivery level.

**Fix patterns (pick one, not both unless needed):**

1. **Cache-busting URL query parameter** in `build_entry.py` — append `?cb=<timestamp>` to the WebView2 URL so WebView2 treats each launch as a fresh request:
   ```python
   import time as _time
   url = f"http://127.0.0.1:{port}/?cb={int(_time.time())}"
   ```

2. **No-cache headers** in the FastAPI static file mount — add `Cache-Control: no-store` to the HTML response. This is the cleaner approach but requires modifying the server config.

**Verify the fix is inside the bundle:** After rebuilding, check `dist/<App>/_internal/desktop_ui/index.html` (the bundled copy) and `dist/<App>/_internal/build_entry.py` (the bundled entry point) to confirm the fix is actually present in the frozen build — NOT just in the source tree. The bundle copies files at build time; if you edit source AFTER building, the old copy is still in the exe.

## Locked directory deletion on Windows — MOVEFILE_DELAY_UNTIL_REBOOT

**Problem:** `rmdir` / `rm -rf` fails with "Device or resource busy" on an empty directory on Windows even when no obvious process holds it open. This is a Windows filesystem lock (often from the MSYS/bash mount layer, antivirus, or a lingering handle from a recently killed process).

**Fix:** Use `MoveFileExW` with `MOVEFILE_DELAY_UNTIL_REBOOT` (flag=4) and `NULL` destination — this schedules the directory for deletion on the next Windows reboot:
```python
import ctypes
kernel32 = ctypes.windll.kernel32
# Schedule deletion on next reboot
ret = kernel32.MoveFileExW(path, None, 4)  # 4 = MOVEFILE_DELAY_UNTIL_REBOOT
if ret == 0:
    print(f"Failed, error: {ctypes.get_last_error()}")
```

Note: MoveFileEx with dest=NULL and MOVEFILE_DELAY_UNTIL_REBOOT does NOT rename the dir — it schedules the actual deletion. The dir remains visible until reboot.

**Alternative:** if you need the dir gone NOW and can reboot: rename it first with the same flag, then delete the renamed dir:
```python
# Rename then delete (rename succeeds even when delete fails on Windows)
kernel32.MoveFileExW(path, path + "_delete_pending", 4)
# After reboot, the "_delete_pending" dir is gone
```

## Import-graph gaps crash new endpoints (500 / NameError)

Adding per-item config helpers (skills/tools/mcp enabled maps) introduced two
silent import bugs that only surface at request time, not import time:
- `tools.py` referenced `config.item_enabled(...)` but had **no `import aether.config`**
  → `/api/tools` returned `500 NameError: name 'config' is not defined`.
- `agent.py` referenced `tools.TOOLS` in a new helper but only imported
  `from .tools import tool_schemas, call_tool` (not the `tools` module) →
  chat returned `500 name 'tools' is not defined`.
**Rule:** any new module-level helper that calls `config.*` or `tools.*` must
`import aether.config as config` / `from . import tools` at the top. After adding
config/agent wiring, smoke-test EVERY new endpoint (curl the GET/POST) before
building the frozen exe — a 500 there costs a full rebuild to rediscover.

## MCP `list_servers()` must NOT spawn subprocesses on the GET

The MCP panel "No MCP servers configured" appearing as a **blocked/empty**
panel or hanging was caused by `list_servers()` calling `connect_all()`, which
spawns each configured server's stdio process (npx, etc.) synchronously inside
the HTTP GET. A bad/missing npx server, or an HTTP server that doesn't respond,
makes the request hang or raise — the UI looks frozen/blocked.
**Fix:** `list_servers()` must be non-blocking and best-effort:
- Iterate configured servers, read `enabled` from config (`item_enabled`).
- Only for **enabled** servers, do a single lightweight `initialize()` probe in
  a `try/except`; set `connected = bool(capabilities)`, terminate the spawned
  proc immediately, and on ANY exception set `connected=False` (never raise).
- `connect_all()` (used by the agent at chat time) should also `continue` past
  disabled/misconfigured servers.
The GET then returns clean JSON (`{"servers":[]}` when none) and the panel
renders; no hang, no 500.

## Settings-panel UI: card-grid layout (this user's spec)

When rendering Skills / Tools / MCP / Memory panels, this user wants the
**server-card grid** (benchmarked against Hermes One), NOT a plain list of rows:
- Fixed left sidebar + scrollable main area; dark high-contrast theme
  (bg `#0b0b12`, panels `#14141f`, accent `#7c6cff`, success `#27c6a1`).
- `grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))` for responsive
  cards; card radius **16px**, generous padding (16px).
- Each card: square rounded icon (top-left) · row of icon buttons (edit ✎,
  delete 🗑) + a **toggle switch** (right) · title (bold) · badges
  (`stdio`/`HTTP` pill + `connected`/`offline` status pill) · monospace subtext
  (the command or URL).
- Toggle switches drive the per-item enable maps (skills/tools/mcp) via
  `POST /api/items/toggle`; the agent reads those maps and auto-wires enabled
  skills/tools/MCP into the prompt at runtime — so "agent must auto-use them"
  is satisfied by enabling-by-default + reading the maps, not by manual wiring.
- Buttons: `border:0; border-radius:8px` (inputs/buttons) vs `16px` (cards).
- **MCP card sub-spec (user's exact layout, v1.2.3):** the MCP panel must match
  Skills/Tools card-for-card. Each card:
  - **Top row:** left = rounded icon + **bold** MCP name; right = a grouped
    cluster of icon buttons — 🧪 **Test Connection** (beaker) immediately
    LEFT of the toggle, 🗑 delete grouped with it, then the **toggle switch**
    (top-right corner).
  - **Bottom row (use-case):** the server's `description` (or command/URL) shown
    in **strict lowercase**, monospace, muted. This footer is the "use case /
    technical config detail" the user specified.
  - **Badges:** a `stdio`/`http` pill + an `enabled`/`disabled` status pill.
  - **Test Connection behavior:** clicking 🧪 hits `POST /api/mcp/test`
    (spawns a REAL stdio process / does a network round-trip), then colors the
    button green (ok, with `connected (N tool(s))`) or red (error, with the
    detail). Never auto-spawns on the GET (see the list_servers pitfall below).
  - **Reasoning Level selector:** a **Chat-topbar** dropdown
    (Auto/Minimal/Low/Standard/High/Max) with the note "Auto is safest. Manual
    levels may be ignored or rejected by models that don't support reasoning
    effort." Persists to `model.reasoning_level` and is passed to OpenRouter via
    `extra_body={"reasoning":{"effort":...}}` in the chat provider call.
- **Hermes-style token savings (Tasks 3/4 parity):** to mirror Hermes' prompt/
  context compression without losing meaning: (a) trim chat history before each
  model call — keep the system prompt + last ~12 user/assistant turns, collapse
  older turns into a one-line `[earlier conversation recap]` system note; (b) cap
  retrieved RAG context (`RETRIEVE_MAX_CHARS`, ~6000) and truncate chunks so the
  whole context stays under budget; (c) return `citations` separately so the UI
  shows a "📚 Sources" footer (Hermes RAG parity). None of these alter the
  visible transcript — only the tokens sent to the model.

## Frozen-config `NameError: name 'sys' is not defined`

A PyInstaller app's `config.py`/`main.py` is read at import time. If any module
level code uses `sys` (e.g. the `getattr(sys, "_MEIPASS", ...)` RAG-DB-bundled
path logic), `sys` MUST be imported at the top of that file. The earlier
session hit `NameError: name 'sys' is not defined` at `config.py:62` because the
bundled-DB path expression used `sys` but `import sys` had been dropped. **Always
`import sys` in any module that references `sys._MEIPASS` / `sys.frozen` /
`sys.argv` for path resolution** — these run at frozen import time where the
module-global namespace is exactly what you imported.

### CRITICAL pywebview pitfall: `create_window()` has NO `icon` kwarg (this build)

In the frozen pywebview version used here, `webview.create_window(...)` does
**NOT** accept an `icon=` argument. Passing it raises at runtime:
`TypeError: create_window() got an unexpected keyword argument 'icon'` — which,
under the "no browser fallback" design, surfaces as the user-facing
*"Aether could not start its native window"* MessageBox (because the webview
try-block catches the TypeError). This was the **actual v1.2.2 launch bug**
after v1.2.1 fixed the mutex.

- **Fix:** drop `icon=` from `create_window`. The icon is set two ways that both
  work: (1) PyInstaller `--icon <logo.ico>` embeds it in the PE (bootloader uses
  it for the window + taskbar), and (2) `webview.start(icon=".../logo.ico")`
  — `webview.start` DOES accept `icon`. So the window icon is covered without
  ever touching `create_window`'s signature.
- **Verify against the actual frozen signature** before trusting the snippet:
  `python -c "import inspect, webview; print(inspect.signature(webview.create_window))"`
  in the same venv the build uses. If `icon` is absent there, it's absent in the
  frozen exe.
- **Symptom triage:** if the user reports the "could not start its native
  window" box, read `aether_launch.log` next to the exe — it contains the real
  traceback. Most causes are (a) `sys`/`Path` undefined (import missing) or (b)
  an invalid kwarg on `create_window`/`start`. WebView2 itself is almost never
  the cause on this machine (runtime is installed).

## The build script MUST actually RUN PyInstaller

A common mistake: the "build script" only copies files to a `_internal/` folder but never invokes PyInstaller. The resulting "executable" is just a Python script that won't run on a machine without the full venv. ALWAYS verify the build runs PyInstaller by checking the output for `INFO: Building EXE`, `INFO: Building COLLECT`, and the final `Build complete!` message. The actual frozen `.exe` will be in `dist_build/<AppName>/<AppName>.exe` (or `dist/<AppName>/<AppName>.exe`), NOT in `_internal/`. If you see only `.py` files and no `base_library.zip` + `python311.dll` + bundled packages, PyInstaller did NOT run.

**Correct build pattern (from working Aether fix):**
```python
# build_exe.py - actual PyInstaller invocation
import PyInstaller.__main__
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

sys.argv = [
    "pyinstaller",
    "--name=Aether",
    "--onedir",
    "--windowed",
    "--icon=desktop_ui/logo.ico",
    "--noconfirm",
    "--clean",
    # Hidden imports for dynamically loaded modules
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
    # Bundled data: UI + sample docs + prebuilt index
    "--add-data=desktop_ui;desktop_ui",
    "--add-data=rag_pdfs;rag_pdfs",
    "--add-data=rag_vector_db;rag_vector_db",
    # Entry point
    "build_entry.py",
]

PyInstaller.__main__.run()

# Post-build: sync data dirs that --add-data sometimes misses
import shutil
OUT = PROJECT_ROOT / "dist" / "Aether"
def _sync(src_name, dst_name=None):
    dst_name = dst_name or src_name
    src = PROJECT_ROOT / src_name
    if not src.exists(): return
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
```

## Health-endpoint polling before WebView2 creation (fixes ERR_CONNECTION_REFUSED)

The single most-reported "app not opening" symptom was the browser error `127.0.0.1 refused to connect` (ERR_CONNECTION_REFUSED). Root cause: `main()` started the uvicorn server in a thread then did `time.sleep(1.5)` and **immediately** handed the URL to `webview.create_window` before the server was actually listening — so WebView2 navigated to a dead port.

**Permanent fix: poll `/api/health` until it returns 200 BEFORE creating the window.** No fixed `sleep`, no random-port fallback, no browser.
- Add `GET /api/health` → `{"ok":true,"version": ...}`.
- In `main()`, after starting the server thread, loop up to ~30s: `urllib.request.urlopen(health_url, timeout=1)`; break on 200.
- If it never comes up: show a MessageBox ("backend server did not become ready...") and exit — NOT a browser tab.
- Also: if `_port_in_use(port)` is true at startup AND it's not our own server (a genuine foreign process holds 8732), show a MessageBox ("port in use by another program") and exit — don't try to bind (which would fail anyway) and don't fall back to a browser.
- Keep the mutex single-instance (focus-existing-window) from the prior fix.
After this change the app cannot produce ERR_CONNECTION_REFUSED: the window is only ever given a URL that is already answering 200.

## Frozen-aware path resolution (like project_rag_hybrid) — CRITICAL

The working `project_rag_hybrid` app uses `app_paths.py` for frozen-aware path resolution. This pattern MUST be used for any app that bundles data (ChromaDB, PDFs, UI) and needs user-writable directories.

**app_paths.py pattern:**
```python
# app_paths.py — frozen-aware path resolution
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
```

**Config.py integration:**
```python
# aether/config.py - Use frozen-aware paths
import app_paths

AETHER_HOME = app_paths.APP_DATA_DIR  # User-writable data dir

# RAG DB path resolution with frozen-aware precedence
"chromadb_path": os.environ.get(
    "RAG_DB_PATH",
    str(app_paths.BASE_DIR / "rag_vector_db")
    if (app_paths.BASE_DIR / "rag_vector_db").is_dir()
    else str(app_paths.CHROMA_DIR),
),
```

This pattern ensures:
- Bundled assets (UI, sample PDFs, prebuilt ChromaDB) are read from `BASE_DIR` (exe folder)
- User data (added PDFs, rebuilt index, settings) goes to `APP_DATA_DIR` (`%LOCALAPPDATA%/Aether`)
- First-run seeding happens automatically via `seed_if_empty()`
- No admin/UAC required for user data operations
