# PyInstaller Build Command (Verified Working - 2026-07-29)

```cmd
pyinstaller --noconfirm --onedir --windowed --name Aether ^
  --icon desktop_ui/logo.ico ^
  --add-data "desktop_ui;desktop_ui" ^
  --add-data "aether;aether" ^
  --hidden-import webview ^
  --hidden-import pythonnet ^
  --hidden-import clr ^
  --hidden-import uvicorn.logging ^
  --hidden-import uvicorn.loops.auto ^
  --hidden-import uvicorn.protocols.http.auto ^
  --hidden-import uvicorn.protocols.websockets.auto ^
  --hidden-import uvicorn.lifespan.on ^
  --hidden-import win32com ^
  --hidden-import win32com.client ^
  --hidden-import winshell ^
  --distpath dist_build ^
  --workpath build_aether ^
  build_entry.py
```

**Critical:** `pythonnet` and `clr` MUST be included for pywebview WinForms backend on Windows. Previously excluded them and app crashed with `ModuleNotFoundError: No module named 'clr'`.

## Build Output Verification

Look for these success markers in PyInstaller output:
```
INFO: Building EXE from EXE-00.toc completed successfully.
INFO: Building COLLECT COLLECT-00.toc completed successfully.
INFO: Build complete! The results are available in: C:\Users\valte\aether\dist_build
```

If you don't see "Building EXE" and "Building COLLECT", PyInstaller didn't run - the build script only copied files.