"""Build a REAL, double-clickable Aether installer (Aether-Setup.exe).

Steps:
  1. Collect the frozen app (dist/Aether.exe) + icon into a zlib payload.
  2. Compile installer_boot.py with PyInstaller (--onefile --windowed),
     bundling the payload as a data file. The result is a genuine PE .exe
     that Windows can launch by double-clicking.

The distributed Aether build contains NO API key — users paste their own
OpenRouter key in the UI (stored only in %APPDATA%/aether/.env).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
APP_EXE = os.path.join(HERE, "dist", "Aether.exe")          # frozen onefile build
APP_ICON = os.path.join(HERE, "desktop_ui", "logo.ico")
BOOT = os.path.join(HERE, "installer_boot.py")
PAYLOAD = os.path.join(HERE, "installer_payload.bin")
OUT = os.path.join(HERE, "dist", "Aether-Setup.exe")


def build_payload() -> None:
    items = []
    with open(APP_EXE, "rb") as fh:
        items.append(("Aether.exe", fh.read()))
    if os.path.exists(APP_ICON):
        with open(APP_ICON, "rb") as fh:
            items.append(("logo.ico", fh.read()))
    manifest = [(rel, len(zlib.compress(data, 9))) for rel, data in items]
    blob = b"".join(zlib.compress(data, 9) for _, data in items)
    with open(PAYLOAD, "wb") as fh:
        fh.write(repr(manifest).encode("utf-8") + b"\x00\x00" + blob)
    print(f"Payload built: {os.path.getsize(PAYLOAD)//1024//1024} MB")


def build_installer() -> None:
    if not os.path.isfile(APP_EXE):
        sys.exit(f"Missing frozen build: {APP_EXE}\nRun PyInstaller first (dist/Aether.exe).")
    build_payload()

    spec_dir = os.path.join(HERE, "build_installer")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--name", "Aether-Setup",
        "--onefile",
        "--windowed",
        f"--add-data", f"{PAYLOAD}{os.pathsep}.",
        "--distpath", os.path.join(HERE, "dist"),
        "--workpath", spec_dir,
        BOOT,
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    # Cleanup intermediate artifacts
    for p in (PAYLOAD, spec_dir):
        if os.path.isfile(p):
            os.remove(p)
        elif os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)

    mb = os.path.getsize(OUT) // 1024 // 1024
    print(f"Built installer: {OUT} ({mb} MB)")


if __name__ == "__main__":
    build_installer()
