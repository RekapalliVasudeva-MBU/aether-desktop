# WebView2 Missing Runtime — Full Fix Pattern

Root cause of "app opens ~2s then closes" on fresh user PCs (pywebview + FastAPI
frozen exe). The dev machine has Edge/WebView2; clean user machines often don't.
`webview.create_window()` throws → silent process death.

## 1. App-level pre-flight (desktop_app.py)

Insert BEFORE the `webview.create_window(...)` call. The key lesson: do NOT assume
the runtime is present — detect, then install-or-message. A bare `create_window()`
with no fallback is the bug.

```python
def _webview2_installed() -> bool:
    try:
        import winreg
        winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications")
        return True
    except Exception:
        pass
    for p in (Path(sys.executable).parent / "WebView2Loader.dll",):
        if p.exists():
            return True
    return False

def _install_webview2() -> bool:
    import urllib.request, subprocess
    boot = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
    dst = Path(os.environ.get("LOCALAPPDATA","")) / "Aether" / "MicrosoftEdgeWebview2Setup.exe"
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(boot, str(dst))
        r = subprocess.run([str(dst), "/silent", "/install"],
                           capture_output=True, text=True, timeout=300)
        return r.returncode in (0, 3010, 1641)
    except Exception:
        return False

if not _webview2_installed():
    if not _install_webview2():
        # message box: point to manual install URL, then exit
        ...
        return
    if not _webview2_installed():
        # 3010/1641 = needs reboot; tell user to restart then relaunch
        ...
        return
```

NOTE: the Evergreen online bootstrapper can hang in a fully headless sandbox
(no interactive consent / network stall). On a real user desktop it installs
fine. The installer-level bundling below is the more reliable path for distribution.

## 2. Installer-level bundling (installer_boot.py + make_installer.py)

Bundle the bootstrapper so the install is fully offline and reliable:

make_installer.py:
```python
WEBVIEW2_BOOT = os.path.join(HERE, "MicrosoftEdgeWebview2Setup.exe")
# in build_payload(): download once if missing
if not os.path.isfile(WEBVIEW2_BOOT):
    urllib.request.urlretrieve("https://go.microsoft.com/fwlink/p/?LinkId=2124703", WEBVIEW2_BOOT)
# add to payload items:
items.append(("MicrosoftEdgeWebview2Setup.exe", open(WEBVIEW2_BOOT,"rb").read()))
```

installer_boot.py (in main(), before launching Aether.exe):
```python
def _webview2_installed():
    try:
        import winreg
        winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications")
        return True
    except Exception:
        return False

def _install_webview2(app_dir):
    import subprocess
    setup = os.path.join(app_dir, "MicrosoftEdgeWebview2Setup.exe")
    if not os.path.isfile(setup):
        return False
    r = subprocess.run([setup, "/silent", "/install"], capture_output=True, text=True, timeout=300)
    return r.returncode in (0, 3010, 1641)

if not _webview2_installed():
    _install_webview2(app_dir)
```

## 3. Verification

- On a machine WITHOUT WebView2: running the old exe crashed at ~2s; the new exe
  stays alive and spawns `msedgewebview2.exe` install processes (proves the guard
  fires instead of crashing).
- Registry key `HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications` appears
  after a successful install.
- Build the installer (`python make_installer.py`) → `dist/Aether-Setup.exe` grows
  by ~1.7MB (the bundled bootstrapper).
