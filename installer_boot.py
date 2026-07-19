"""Aether self-extracting installer boot (compiled to a real .exe via PyInstaller).

Reads the embedded payload (built by make_installer.py) from sys._MEIPASS,
extracts Aether.exe + logo.ico to %LOCALAPPDATA%/Aether, creates Desktop +
Start Menu shortcuts, then launches the app.
"""
import os
import sys
import zlib
import ast

PAYLOAD_NAME = "installer_payload.bin"


def _payload_path():
    # When frozen by PyInstaller, data files live under sys._MEIPASS.
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, PAYLOAD_NAME)


def _kill_running_apps():
    """Close any already-running Aether so we can overwrite its files."""
    import subprocess
    myself = os.path.basename(sys.executable).lower()
    for name in ("aether.exe", "aether-setup.exe"):
        if name == myself:
            continue
        try:
            subprocess.run(["taskkill", "/F", "/IM", name],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=10)
        except Exception:
            pass
    # give the OS a moment to release file handles
    import time
    time.sleep(1.5)


def _write_with_retry(dp, chunk, attempts=5):
    for i in range(attempts):
        try:
            with open(dp, "wb") as out:
                out.write(chunk)
            return
        except PermissionError:
            if i == attempts - 1:
                raise
            _kill_running_apps()


def _webview2_installed() -> bool:
    """True if the Microsoft WebView2 Runtime is present (registry check)."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications",
        )
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def _install_webview2(app_dir: str) -> bool:
    """Silently install the bundled WebView2 Evergreen Runtime."""
    import subprocess
    setup = os.path.join(app_dir, "MicrosoftEdgeWebview2Setup.exe")
    if not os.path.isfile(setup):
        return False
    try:
        r = subprocess.run([setup, "/silent", "/install"],
                           capture_output=True, text=True, timeout=300)
        return r.returncode in (0, 3010, 1641)
    except Exception:
        return False


def main():
    payload_path = _payload_path()
    with open(payload_path, "rb") as fh:
        raw = fh.read()
    head, blob = raw.split(b"\x00\x00", 1)
    manifest = ast.literal_eval(head.decode("utf-8"))

    app_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Aether")
    os.makedirs(app_dir, exist_ok=True)

    _kill_running_apps()

    # Prerequisite: ensure WebView2 Runtime is present (pywebview needs it).
    # A missing runtime is the #1 cause of 'app opens 2s then closes'.
    if not _webview2_installed():
        print("[installer] WebView2 missing — installing from bundled bootstrapper")
        _install_webview2(app_dir)

    off = 0
    for rel, n in manifest:
        chunk = zlib.decompress(blob[off:off + n])
        off += n
        dp = os.path.join(app_dir, rel)
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        _write_with_retry(dp, chunk)

    # Shortcuts (best-effort; pywin32 may not be present in all runtimes).
    try:
        import winshell
        from win32com.client import Dispatch
        icon = os.path.join(app_dir, "logo.ico")
        exe_path = os.path.join(app_dir, "Aether.exe")
        for lnk in (os.path.join(winshell.desktop(), "Aether.lnk"),
                    os.path.join(winshell.start_menu(), "Programs", "Aether.lnk")):
            sc = Dispatch("WScript.Shell").CreateShortcut(lnk)
            sc.Targetpath = exe_path
            sc.WorkingDirectory = app_dir
            if os.path.exists(icon):
                sc.IconLocation = icon
            sc.save()
    except Exception as e:
        print("shortcut skip:", e)

    try:
        os.startfile(os.path.join(app_dir, "Aether.exe"))
    except Exception:
        pass


if __name__ == "__main__":
    main()
