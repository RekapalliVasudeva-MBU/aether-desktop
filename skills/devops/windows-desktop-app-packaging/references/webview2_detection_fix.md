# WebView2 Detection Fix - Permanent Solution

## Problem
The app kept showing "WebView2 runtime missing — attempting install" even though WebView2 was installed (verified: version 150.0.4078.99 at `C:\Program Files (x86)\Microsoft\EdgeWebView\Application`).

Root cause: `_webview2_installed()` checked the wrong registry key:
- **Wrong**: `HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications`
- **Correct**: `HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}`

The Evergreen runtime registers at the EdgeUpdate\Clients key with the fixed GUID.

## Verification
```powershell
# This works - WebView2 is installed
Get-ItemProperty 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
# Returns: pv = 150.0.4078.99

# This fails - wrong key
Get-ItemProperty 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications'
# Returns: nothing (key doesn't exist)
```

## Permanent Fix: Two-Layer Defense

### 1. App-Level Pre-Flight (Runs at Every Launch)
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
    except Exception as e:
        print(f"[desktop] WebView2 EdgeUpdate key check failed: {e}")
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
    except Exception as e:
        print(f"[desktop] WebView2 EdgeWebView key check failed: {e}")
        pass
    # Also accept a side-by-side WebView2 in the app folder (bundled).
    try:
        for p in (Path(sys.executable).parent / "WebView2Loader.dll",
                  Path(sys.executable).parent / "_internal" / "WebView2Loader.dll"):
            if p.exists():
                return True
    except Exception as e:
        print(f"[desktop] WebView2 local DLL check failed: {e}")
        pass
    return False


def _install_webview2() -> bool:
    """Download and silently install the WebView2 Evergreen Runtime.

    Returns True on success. Shows a progress box while downloading.
    """
    import urllib.request
    import subprocess
    url = ("https://go.microsoft.com/fwlink/p/?LinkId=2124703"
           "  # WebView2 Evergreen bootstrapper")
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


# PERMANENT FIX: Run BEFORE webview.create_window()
if not _webview2_installed():
    print("[desktop] WebView2 runtime missing — attempting install")
    if not _install_webview2():
        return
    if not _webview2_installed():
        _fail_box(
            "Aether installed the WebView2 Runtime but it isn't active yet.\n\n"
            "Please restart your computer once, then relaunch Aether."
        )
        return
```

### 2. Installer-Level Bundling (`make_installer.py` + `installer_boot.py`)
```python
# make_installer.py - Download bootstrapper at build time
WEBVIEW2_BOOT = os.path.join(HERE, "MicrosoftEdgeWebview2Setup.exe")
if not os.path.isfile(WEBVIEW2_BOOT):
    urllib.request.urlretrieve(
        "https://go.microsoft.com/fwlink/p/?LinkId=2124703", WEBVIEW2_BOOT)

# Add to payload
# ... included in installer payload

# installer_boot.py - Runs at install time
def _install_webview2(app_dir: str) -> bool:
    setup = os.path.join(app_dir, "MicrosoftEdgeWebview2Setup.exe")
    if not os.path.isfile(setup):
        return False
    r = subprocess.run([setup, "/silent", "/install"],
                       capture_output=True, text=True, timeout=300)
    return r.returncode in (0, 3010, 1641)
```

## Detection Locations (Priority Order)
1. `HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}` (Evergreen official)
2. `HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications` (Alternate)
3. `WebView2Loader.dll` next to exe (bundled/side-by-side)
4. `WebView2Loader.dll` in `_internal/` (PyInstaller bundled)

## Verification
- Fresh Windows VM → double-click Aether.exe → shows "Installing WebView2" → completes → app opens
- WebView2 already installed → no prompt, app opens immediately
- Auto-install fails → clear message box with manual install URL

## Files
- `C:/Users/valte/aether/desktop_app.py` (lines 1199-1302)
- `C:/Users/valte/aether/make_installer.py` (bootstrapper download + payload inclusion)
- `C:/Users/valte/aether/installer_boot.py` (install-time WebView2 install)

## Prevention
- Always check WebView2 BEFORE calling `webview.create_window()`
- Show user-friendly message with progress, not a silent crash
- Bundle bootstrapper in installer for offline installs
- Accept side-by-side WebView2 as valid (portable installs)