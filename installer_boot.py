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


def main():
    payload_path = _payload_path()
    with open(payload_path, "rb") as fh:
        raw = fh.read()
    head, blob = raw.split(b"\x00\x00", 1)
    manifest = ast.literal_eval(head.decode("utf-8"))

    app_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Aether")
    os.makedirs(app_dir, exist_ok=True)

    off = 0
    for rel, n in manifest:
        chunk = zlib.decompress(blob[off:off + n])
        off += n
        dp = os.path.join(app_dir, rel)
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        with open(dp, "wb") as out:
            out.write(chunk)

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
