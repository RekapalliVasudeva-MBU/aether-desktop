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
# The REAL app is the onedir build produced by `build_aether.py`:
#   dist_build/Aether/  (Aether.exe + _internal/ + support files)
# We bundle this WHOLE FOLDER as the payload, not a single .exe, so the
# extracted app is complete and runnable (the earlier bug bundled the
# installer .exe itself, causing an infinite re-launch loop).
APP_DIR = os.path.join(HERE, "dist_build", "Aether")
APP_EXE = os.path.join(APP_DIR, "Aether.exe")
APP_ICON = os.path.join(HERE, "desktop_ui", "logo.ico")
# WebView2 Evergreen bootstrapper — bundled so the installer can install the
# runtime on machines that don't have it (the #1 cause of 'app opens 2s then
# closes' on fresh user PCs). Downloaded once at build time if missing.
WEBVIEW2_BOOT = os.path.join(HERE, "MicrosoftEdgeWebview2Setup.exe")
# Prebuilt ChromaDB vector DB (582 chunks, RAG knowledge base). Shipped inside
# the installer so RAG works out of the box with zero config. If missing, the
# app still runs — RAG just returns "not enough information" until a DB exists.
RAG_DB_SRC = os.path.join(HERE, "..", "project_rag", "rag_vector_db")
BOOT = os.path.join(HERE, "installer_boot.py")
PAYLOAD = os.path.join(HERE, "installer_payload.bin")
OUT = os.path.join(HERE, "dist", "Aether-Setup.exe")


def build_payload() -> None:
    # Ensure the WebView2 bootstrapper is available to bundle.
    if not os.path.isfile(WEBVIEW2_BOOT):
        print("Downloading WebView2 Evergreen bootstrapper…")
        import urllib.request
        urllib.request.urlretrieve(
            "https://go.microsoft.com/fwlink/p/?LinkId=2124703", WEBVIEW2_BOOT
        )
    items = []
    for root, _dirs, files in os.walk(APP_DIR):
        for fn in files:
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, APP_DIR)
            with open(full, "rb") as fh:
                items.append((rel, fh.read()))
    if os.path.exists(APP_ICON):
        with open(APP_ICON, "rb") as fh:
            items.append((os.path.join("desktop_ui", "logo.ico"), fh.read()))
    # Bundle the WebView2 bootstrapper so the installer can install the
    # runtime on machines that lack it.
    if os.path.isfile(WEBVIEW2_BOOT):
        with open(WEBVIEW2_BOOT, "rb") as fh:
            items.append(("MicrosoftEdgeWebview2Setup.exe", fh.read()))
    # Bundle the prebuilt RAG vector DB (if present) under rag_vector_db/
    if os.path.isdir(RAG_DB_SRC):
        for root, _dirs, files in os.walk(RAG_DB_SRC):
            for fn in files:
                full = os.path.join(root, fn)
                rel = os.path.join(
                    "rag_vector_db", os.path.relpath(full, RAG_DB_SRC)
                )
                with open(full, "rb") as fh:
                    items.append((rel, fh.read()))
    manifest = [(rel, len(zlib.compress(data, 9))) for rel, data in items]
    blob = b"".join(zlib.compress(data, 9) for _, data in items)
    with open(PAYLOAD, "wb") as fh:
        fh.write(repr(manifest).encode("utf-8") + b"\x00\x00" + blob)
    print(f"Payload built: {os.path.getsize(PAYLOAD)//1024//1024} MB "
          f"({len(items)} files)")


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
