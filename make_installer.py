"""Self-contained Aether installer (no Inno Setup / no external download).

Usage (run from the aether project root after PyInstaller built dist/Aether.exe):
    python make_installer.py

Produces dist/Aether-Setup.exe — a single portable Windows installer that:
  1. Extracts Aether.exe to %LOCALAPPDATA%/Aether/ (+ logo.ico for the shortcut)
  2. Creates a Desktop shortcut + Start Menu shortcut (with the Aether icon)
  3. Launches Aether on finish

Format: <boot_python_script> + b"\n__PAYLOAD__\n" + <manifest_bytes> + b"\x00\x00" + <zlib_blob>
The boot script parses the payload by reading itself (sys.executable / __file__).

The distributed Aether build contains NO API key — users paste their own
OpenRouter key in the UI (stored only in %APPDATA%/aether/.env).
"""
from __future__ import annotations
import ast
import os
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
APP_EXE = os.path.join(HERE, "dist", "Aether.exe")        # frozen onefile build
APP_ICON = os.path.join(HERE, "desktop_ui", "logo.ico")


def _collect():
    items = []
    # the frozen executable
    with open(APP_EXE, "rb") as fh:
        items.append(("Aether.exe", fh.read()))
    # icon for the shortcut
    if os.path.exists(APP_ICON):
        with open(APP_ICON, "rb") as fh:
            items.append(("logo.ico", fh.read()))
    return items


def build_payload() -> bytes:
    items = _collect()
    manifest = [(rel, len(zlib.compress(data, 9))) for rel, data in items]
    blob = b"".join(zlib.compress(data, 9) for _, data in items)
    return repr(manifest).encode("utf-8") + b"\x00\x00" + blob


INSTALLER_BOOT = r'''
import ast, os, sys, zlib

def main():
    exe = sys.executable if getattr(sys, "frozen", False) else __file__
    raw = open(exe, "rb").read()
    marker = b"\n__PAYLOAD__\n"
    idx = raw.find(marker)
    tail = raw[idx + len(marker):]
    head, blob = tail.split(b"\x00\x00", 1)
    manifest = ast.literal_eval(head.decode("utf-8"))
    app_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Aether")
    os.makedirs(app_dir, exist_ok=True)
    off = 0
    for rel, n in manifest:
        chunk = zlib.decompress(blob[off:off + n]); off += n
        dp = os.path.join(app_dir, rel)
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        open(dp, "wb").write(chunk)
    # shortcuts (best-effort)
    try:
        import winshell
        from win32com.client import Dispatch
        icon = os.path.join(app_dir, "logo.ico")
        exe_path = os.path.join(app_dir, "Aether.exe")
        for lnk in (os.path.join(winshell.desktop(), "Aether.lnk"),
                    os.path.join(winshell.start_menu(), "Programs", "Aether.lnk")):
            sc = Dispatch("WScript.Shell").CreateShortcut(lnk)
            sc.Targetpath = exe_path; sc.WorkingDirectory = app_dir
            if os.path.exists(icon): sc.IconLocation = icon
            sc.save()
    except Exception as e:
        print("shortcut skip:", e)
    try: os.startfile(os.path.join(app_dir, "Aether.exe"))
    except Exception: pass

if __name__ == "__main__":
    main()
'''


def main():
    if not os.path.isfile(APP_EXE):
        sys.exit(f"Missing frozen build: {APP_EXE}\nRun PyInstaller first (dist/Aether.exe).")
    payload = build_payload()
    out = os.path.join(HERE, "dist", "Aether-Setup.exe")
    with open(out, "wb") as fh:
        fh.write(INSTALLER_BOOT.encode("utf-8") + b"\n__PAYLOAD__\n" + payload)
    mb = os.path.getsize(out) // 1024 // 1024
    print(f"Built installer: {out} ({mb} MB)")


if __name__ == "__main__":
    main()
