# WebView2 Auto-Install — Detailed Reference

## Registry Check (Exact Path)
```python
winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
               r"SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications")
```
**Note**: Not `EdgeWebView2` or `Edge` — exactly `EdgeWebView\Applications`

## Bootstrapper
- **URL**: `https://go.microsoft.com/fwlink/p/?LinkId=2124703` (official Evergreen, redirects)
- **File**: `MicrosoftEdgeWebview2Setup.exe` (~1.5 MB)
- **Silent install**: `/silent /install`
- **Accepted return codes**: `0` (ok), `3010` (reboot required), `1641` (reboot required)

## Side-by-Side Loader (Alternative)
Place `WebView2Loader.dll` in:
- `dist_build/AppName/` (app root)
- `dist_build/AppName/_internal/` (PyInstaller internal)

Check both locations in `_webview2_installed()`.

## Desktop App Entry Point Pattern (desktop_app.py)

```python
def _webview2_installed() -> bool:
    try:
        import winreg
        winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications")
        return True
    except Exception:
        pass
    for p in (Path(sys.executable).parent / "WebView2Loader.dll",
              Path(sys.executable).parent / "_internal" / "WebView2Loader.dll"):
        if p.exists():
            return True
    return False

def _install_webview2() -> bool:
    import urllib.request, subprocess
    boot = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
    dst = Path(os.environ.get("LOCALAPPDATA", "")) / "Aether" / "MicrosoftEdgeWebview2Setup.exe"
    dst.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(boot, str(dst))
    r = subprocess.run([str(dst), "/silent", "/install"],
                       capture_output=True, text=True, timeout=300)
    return r.returncode in (0, 3010, 1641)

# GUARD BEFORE ANY pywebview IMPORT
if not _webview2_installed():
    if not _install_webview2():
        _fail_box("WebView2 install failed — see manual install URL")
        return
    if not _webview2_installed():
        _fail_box("WebView2 installed but not active — reboot required")
        return
```

## Installer Bootstrapper (installer_boot.py)

```python
def _webview2_installed() -> bool:
    try:
        import winreg
        winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications")
        return True
    except Exception:
        return False

def _install_webview2(app_dir: str) -> bool:
    import subprocess
    setup = os.path.join(app_dir, "MicrosoftEdgeWebview2Setup.exe")
    if not os.path.isfile(setup):
        return False
    r = subprocess.run([setup, "/silent", "/install"],
                       capture_output=True, text=True, timeout=300)
    return r.returncode in (0, 3010, 1641)

def main():
    # ... extraction logic ...
    if not _webview2_installed():
        print("[installer] WebView2 missing — installing from bundled bootstrapper")
        _install_webview2(app_dir)
    # ... continue ...
```

## make_installer.py — Bundle Bootstrapper

```python
WEBVIEW2_BOOT = os.path.join(HERE, "MicrosoftEdgeWebview2Setup.exe")

def build_payload():
    if not os.path.isfile(WEBVIEW2_BOOT):
        print("Downloading WebView2 Evergreen bootstrapper…")
        import urllib.request
        urllib.request.urlretrieve(
            "https://go.microsoft.com/fwlink/p/?LinkId=2124703", WEBVIEW2_BOOT
        )
    # ... existing items ...
    if os.path.isfile(WEBVIEW2_BOOT):
        with open(WEBVIEW2_BOOT, "rb") as fh:
            items.append(("MicrosoftEdgeWebview2Setup.exe", fh.read()))
```

## Bootstrapper URL & Return Codes
- **URL**: `https://go.microsoft.com/fwlink/p/?LinkId=2124703` (official Evergreen, redirects)
- **Success codes**: `0` (ok), `3010` (reboot required), `1641` (reboot required)

## Frozen Crash Dump Pattern

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

## Frozen-Build Pitfall: Icon kwarg
**pywebview `create_window()` in frozen builds has NO `icon` kwarg** — dev import check passes but frozen exe throws. The icon MUST come from PyInstaller `--icon=logo.ico`.

## Debugging Checklist for "Opens 2s Then Closes"
1. Run frozen exe from terminal: `./Aether.exe` → captures traceback
2. Check `run.log` in `%LOCALAPPDATA%\Aether\`
3. Verify WebView2 registry key: `HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications`
4. Verify `WebView2Loader.dll` in `dist_build/Aether/` or `_internal/`
4. Test with `AETHER_HEADLESS=1` to isolate server vs UI crash