---
name: windows-app-launch-debug
description: Diagnose and fix a Windows desktop app that "won't open" / "double-click does nothing" / launches silently and exits — especially PyInstaller-frozen Python apps (pywebview/FastAPI/Electron-style) using a single-instance named mutex. Covers live root-cause inspection (running processes, port bindings, window enumeration) and the exact ctypes pitfalls that bite mutex/ window-focus code. Use whenever the user reports an installed .exe fails to launch, the app icon does nothing, or a second launch silently fails.
---

# Windows App Launch Debug

When the user says "the app won't open", "double-click does nothing", or "it
launches but nothing shows" for an installed Windows `.exe`, treat it as a
**FUNDAMENTAL failure** (per user rule: a feature that silently fails is not
done). Do NOT guess, do NOT claim fixed without reproducing the exact reported
launch path. Verify against the REAL running artifact, not a backend import.

This skill covers the most common class for this user's Aether desktop app
(PyInstaller `--onedir` + Inno Setup, FastAPI server + pywebview window,
single-instance named mutex), but the technique generalizes.

## Step 0 — Resist the wrong blame

A repo/code change to *docs* or *source that isn't the running artifact* cannot
break the installed exe. Confirm what the launcher actually points at:

```bash
powershell -NoProfile -Command "(New-Object -ComObject WScript.Shell).CreateShortcut('C:\\Users\\valte\\OneDrive\\Desktop\\Aether.lnk').TargetPath"
```

The `.lnk` usually points at the **installed** path (`%LOCALAPPDATA%\\Aether\\Aether.exe`),
NOT the dev repo build — in which case "I edited the repo" is almost never the cause
of a launch failure, since the installed exe is a separate frozen build.

**Exception**: When the shortcut points to a dev build directory (e.g.
`C:\Users\valte\aether\dist\Aether\Aether.exe`), the issue is almost always one of:
1. **Old process still running** holding the port/file lock — kill it before rebuilding.
2. **Build failed silently** — check the build log for `PermissionError` on the exe
   (PyInstaller can't overwrite a running file).

Always verify with `tasklist | grep -i aether` and `netstat -ano | grep :8732` before
blaming source code changes.

## Step 1 — Live root-cause inspection (no guessing)

Run these from the Hermes terminal (bash/git-bash on Windows). Each answers a
specific hypothesis:

**Is the app already running (stale instance holding a mutex)?**
```bash
tasklist 2>/dev/null | grep -i aether
```

**Is the server port actually listening? (a server can be up while its window is dead)**
```bash
netstat -ano 2>/dev/null | grep -E ':8732'
# then map the PID:  netstat -ano | grep <PID>
```

**Does the running instance own a REAL visible window, or only helper windows?**
A healthy app owns a visible window. A "server alive but window dead" instance
owns only `GDI+ Window (Aether.exe)` / `Default IME` (both invisible). Detect with
this ctypes probe (run as a Python one-liner):

```python
import ctypes
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
EnumWindows = user32.EnumWindows
IsWindowVisible = user32.IsWindowVisible
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
def cb(hwnd, _):
    if not IsWindowVisible(hwnd): return True
    pid = ctypes.c_int(); GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == 31104:  # the suspect PID
        ln = user32.GetWindowTextLengthW(hwnd)
        b = ctypes.create_unicode_buffer(ln + 1)
        user32.GetWindowTextW(hwnd, b, ln + 1)
        print("hwnd", hwnd, "visible", IsWindowVisible(hwnd), "title", repr(b.value))
    return True
EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(cb), 0)
```

If the only windows for that PID are `GDI+ Window` / `Default IME` → the WebView
window died but the server + mutex survived. **That is the "won't open" bug:**
a second launch sees mutex-held + server-alive, assumes the other instance is
fine, tries to focus a non-existent window, and silently exits.

**Additional signal: WebView2 runtime MISSING (the "opens 2s then closes" cause on FRESH user PCs)** — separate from the dead-mutex case above, requires a pre-flight check before `create_window()`.

## Step 1.5 — WebView2 Runtime MISSING (the "opens 2s then closes" cause on FRESH user PCs)

A second, distinct root cause of "app launches then vanishes in ~2s" — separate
from the dead-mutex case above — is a **missing Microsoft WebView2 Runtime**.
`pywebview` (the `create_window()` call) requires it; if absent, the call throws
and the frozen exe dies silently with no window. This is the #1 cause of
"installed app won't open for OTHER users" while it works fine on the dev's
machine (dev has Edge/WebView2; clean user PC often doesn't).

**Detect (registry check):**
```python
import winreg
try:
    winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                   r"SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications")
    # present
except Exception:
    # MISSING -> this is the bug
```
Also accept a side-by-side `WebView2Loader.dll` next to the exe (bundled runtime).

**Symptom signature:** running the frozen exe shows `Failed to unregister class
Chrome_WidgetWin_0` (a WebView2 window-class collision) OR the process exits
within ~2s with no window and no error box. The mutex/dead-window case (Step 1)
instead shows a *server still listening* on the port — WebView2-missing shows NO
listening server because it dies before/at window creation.

**Fix (permanent, in the app):** add a pre-flight check BEFORE `webview.create_window()`
that auto-installs the Evergreen Runtime if missing, with a clear fallback message
instead of a silent crash:
```python
def _webview2_installed() -> bool:
    """True if the Microsoft WebView2 Runtime is present on this machine.

    pywebview needs it to render the window. A missing runtime is the
    #1 cause of 'app opens for 2 seconds then closes' on fresh user PCs.
    """
    try:
        import winreg
        # Evergreen runtime registers here:
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
    """Download + silently install the WebView2 Evergreen Runtime.

    Returns True on success. Shows a progress box while downloading.
    """
    import urllib.request
    import subprocess
    url = ("https://go.microsoft.com/fwlink/p/?LinkId=2124703"
           "  # WebView2 Evergreen bootstrapper")
    # The fwlink above redirects; use the direct bootstrapper URL:
    boot = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
    dst = Path(os.environ.get("LOCALAPPDATA", "")) / "Aether" / "MicrosoftEdgeWebview2Setup.exe"
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                "Aether needs the Microsoft WebView2 Runtime (one-time "
                "install, ~1.5 MB download). Installing now…\n\n"
                "If this fails, install it manually from:\n"
                "https://developer.microsoft.com/microsoft-edge/webview2/",
                "Aether", 0x40,
            )
        except Exception:
            pass
        print("[desktop] downloading WebView2 runtime bootstrapper…")
        urllib.request.urlretrieve(boot, str(dst))
        print("[desktop] running WebView2 installer (silent)…")
        r = subprocess.run([str(dst), "/silent", "/install"],
                            capture_output=True, text=True, timeout=300)
        ok = r.returncode in (0, 3010, 1641)  # 0 ok, 3010/1641 reboot required (still installed)
        print(f"[desktop] WebView2 installer rc={r.returncode} ok={ok}")
        return ok
    except Exception as e:
        print(f"[desktop] WebView2 auto-install failed: {e}")
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                "Aether could not auto-install the WebView2 Runtime.\n\n"
                "Please install it manually (free, ~1.5 MB) from:\n"
                "https://developer.microsoft.com/microsoft-edge/webview2/\n\n"
                "Then relaunch Aether.",
                "Aether", 0x10,
            )
        except Exception:
            pass
        return False

# PERMANENT fix for the 'opens 2s then closes' bug: ensure WebView2 is
# present BEFORE we ever touch pywebview. If missing, install it (or tell
# the user) instead of crashing silently.
if not _webview2_installed():
    print("[desktop] WebView2 runtime missing — attempting install")
    if not _install_webview2():
        try:
            kernel32.ReleaseMutex(mutex)
        except Exception:
            pass
        return
    # Installed (possibly needs reboot for 3010); try to continue.
    if not _webview2_installed():
        _fail_box(
            "Aether installed the WebView2 Runtime but it isn't active yet.\n\n"
            "Please restart your computer once, then relaunch Aether."
        )
        try:
            kernel32.ReleaseMutex(mutex)
        except Exception:
            pass
        return
```

If `_webview2_installed()` is False → call `_install_webview2()`; if that fails,
show a message box pointing to https://developer.microsoft.com/microsoft-edge/webview2/
and exit. Do NOT call `create_window()` until the runtime is present.

**Fix (installer):** bundle the bootstrapper (`MicrosoftEdgeWebview2Setup.exe`,
~1.7MB, from the fwlink above) into the installer payload and run it `/silent
/install` during setup (in `installer_boot.py`, before launching the app). This
makes new users never hit the missing-runtime crash. Full pattern in
`references/webview2_missing_runtime.md`.

**Installer changes made in this session:**
- `make_installer.py`: Added `WEBVIEW2_BOOT` constant and download logic in `build_payload()` to fetch and bundle the WebView2 bootstrapper (`MicrosoftEdgeWebview2Setup.exe`) into the installer payload.
- `installer_boot.py`: Added `_webview2_installed()` and `_install_webview2()` functions, plus a pre-launch check that installs the bundled WebView2 bootstrapper silently before launching the app.

**git-bash `cmd /c` PATH-DOUBLING QUIRK (cost this session 10+ wasted calls):**
When you run a Windows binary via `cmd /c "C:\Users\valte\cloudflared.exe ..."`
from the Hermes git-bash terminal, MSYS sometimes rewrites the absolute path into
`C:\c\Users\valte\cloudflared.exe` (prefixing a spurious `c\`), so the binary is
"not found". Symptom: `dir /s /b C:\Users\valte\cloudflared.exe` returns
`C:\c\Users\valte\cloudflared.exe` (the doubled path) even though the file is real.
Workarounds that actually work:
  * Call the exe directly from a Python `subprocess.run([r"C:\Users\valte\cloudflared.exe", ...])`
    (bypasses `cmd` path rewriting entirely).
  * Or write a tiny `.ps1` and run `powershell -ExecutionPolicy Bypass -File x.ps1`.
  * `wmic`/`Get-CimInstance ExecutablePath` returns empty for LocalSystem services —
    don't rely on it to locate a service's binary.
Verify a binary's real presence with `Test-Path` in PowerShell, not git-bash `ls`.

## Step 2 — The fix pattern (single-instance mutex)

The launcher's "is the other instance usable?" check must require a **visible
window owned by the app exe**, not just a live HTTP port. Server-up-but-window-dead
must be treated as dead → take over (release mutex, start fresh).

The robust "does another instance have a usable window?" predicate:

1. `EnumWindows` over visible windows.
2. For each, `GetWindowThreadProcessId` → skip our own PID.
3. **Scope by executable name** — open the window's process with
   `OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)` and read its exe path
   with `psapi.GetModuleFileNameExW`. Accept only windows whose exe ends with
   `aether.exe`. Do NOT match on a brittle title string, and do NOT accept "any
   visible window from another PID" (false-positives on Explorer/other apps).
4. Skip helper windows (`GDI+ Window`, `Default IME`).
5. If `found` is empty → no usable window → the other instance is dead → take over.

See `references/mutex-window-predicate.md` for the exact working predicate and
the focus-raise sequence (`AttachThreadInput` + `ShowWindow(SW_RESTORE)` +
`SetForegroundWindow`).

## Step 3 — CRITICAL ctypes pitfall: GetModuleFileNameExW is in PSAPI

`GetModuleFileNameExW` is **NOT** resolvable via `ctypes.windll.kernel32` — it
lives in `psapi` (sometimes forwarded, but `windll.kernel32.GetModuleFileNameExW`
raises `AttributeError` on many builds). Load it explicitly:

```python
psapi = ctypes.windll.psapi
psapi.GetModuleFileNameExW(hproc, 0, buf, 1024)
```

A bare `kernel32.GetModuleFileNameExW = kernel32.GetModuleFileNameExW` assignment
inside a `try` will throw and (if swallowed) silently break the predicate, making
it always return "no window". This was the exact bug that masked the real fix.

## Step 4 — Verify WITHOUT an unwinnable mock harness

You CANNOT exercise a Windows GUI/mutex path headlessly, and mocking ctypes
callbacks (`EnumWindows` with a fake `cb`) is a trap — `byref(pid)` passes a
`CArgObject` your mock can't `.value`, and you'll burn many iterations fighting
the harness instead of the code. Instead verify with:

1. **Syntax/parse check** — `python -c "import ast; ast.parse(open('desktop_app.py',encoding='utf-8').read())"`.
2. **Static reachability grep** — confirm the append/decision line is NOT nested
   under a `return` (a patch-induced wrong indent made `found.append` unreachable
   in this session). `grep -n "found.append\|if not is_aether:\|return len(found)" file.py`.
3. **Real frozen build** — run the project's `build_aether.py` (or equivalent)
   in the background; confirm it completes. The installed exe is the only true
   runtime. Then have the user relaunch the `.lnk`.

For the dead-instance decision logic, you CAN unit-test it headlessly: stand up a
`http.server` on the port returning 200 at `/api/health`, run the predicate with
NO Aether window present → must return `False` (take over). That case needs no GUI.

## Step 5 — Unblock the user immediately

Kill the stale instance so they can use the app NOW (the fix is for the NEXT build):
```bash
taskkill /PID <stale_pid> /F
sleep 2
netstat -ano | grep -E ':8732' && echo "STILL LISTENING" || echo "port free"
```
Then tell them to double-click the `.lnk` — it will open fresh.

## Commit + push discipline

- Commit the source fix (e.g. `desktop_app.py`) with a root-cause commit message.
- Push to the user's repo (respect the private-repo rule; if the repo is already
  public, do NOT change visibility — flag it).
- Build artifacts / `.log` files: NEVER `git add -A`; stage only the source fix.

## Related skills
- `windows-desktop-app-packaging` — building/freezing the exe (complements this:
  this skill debugs the built exe; that one builds it).
- `gstack-method` — the ship discipline; apply its "verify the real path" rule here.
- `python-dev` — Windows Python env pitfalls.
