# WebView2 Missing Runtime — Permanent Fix

The #1 cause of "app opens 2s then closes" on fresh Windows machines for pywebview-based apps.

## Detection

```python
import winreg
try:
    winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                   r"SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications")
    # present
except Exception:
    # MISSING -> this is the bug
```

## Permanent Fix (Two Layers)

### 1. App-level pre-flight (desktop_app.py) — runs at EVERY launch

```python
def _webview2_installed() -> bool:
    try:
        winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications")
        return True
    except Exception:
        pass
    # side-by-side WebView2Loader.dll also accepted
    for p in (Path(sys.executable).parent / "WebView2Loader.dll",
              Path(sys.executable).parent / "_internal" / "WebView2Loader.dll"):
        if p.exists(): return True
    return False

def _install_webview2() -> bool:
    # download Evergreen bootstrapper, run /silent /install, show progress box
    # return True on success
```

If missing → auto-install or show a message box with the manual install URL. **Do NOT call `create_window()` until the runtime is present.**

### 2. Installer-level bundling (`make_installer.py` + `installer_boot.py`)

Download the 1.7 MB Evergreen bootstrapper (`https://go.microsoft.com/fwlink/p/?LinkId=2124703`) at build time, bundle it into the payload, and run it `/silent /install` during setup BEFORE launching the app. Payload size increases by ~1.7 MB.

Full implementation pattern verified in this session.