# Aether Desktop App Build Fix — 2026-07-30

## Problem
Aether.exe crashed on launch with `ModuleNotFoundError: No module named 'unicodedata'` after the aether package import was fixed.

## Root Cause Chain
`desktop_app_fixed.py:30` → `from aether import config, agent, pdf_store, rag` → `aether/telegram.py` → `import requests` → `requests/packages.py` → `import idna` → `idna/core.py` → `import unicodedata` (C extension not auto-included by PyInstaller in `--windowed` mode)

## Fix Applied to build_exe.py
1. `--collect-all=aether` + `--paths=C:/Users/valte/aether` — bundles local aether package
2. `--hidden-import=unicodedata` — C extension needed by requests→idna chain
3. Removed `--clean` flag — was causing 5+ minute timeouts on every rebuild
4. Added `--hidden-import=app_paths`, `--hidden-import=win32api` as defensive imports

## Build Command
```powershell
cd C:\Users\valte\aether
python build_exe.py
```

## Verification After Build
```powershell
Test-Path C:\Users\valte\aether\dist\Aether\_internal\aether\__init__.py
Test-Path C:\Users\valte\aether\dist\Aether\_internal\unicodedata.pyd
```

## Launch
```powershell
Start-Process C:\Users\valte\aether\dist\Aether\Aether.exe
# Wait 5s then verify:
curl http://127.0.0.1:8732/api/health
```

## Key Insight
`--collect-all=aether` bundles Python .py files but does NOT pull in C extensions from transitive dependencies (unicodedata, _socket, ssl). Those need explicit `--hidden-import`.