---
name: app-auto-update-crash-reporting
description: Desktop app auto-update with GitHub Releases, crash reporting, and crash log collection.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
category: devops
tags: [auto-update, crash-reporting, github-releases, desktop-app, pyinstaller, win32]
---

# App Auto-Update & Crash Reporting Skill

## Overview
Production desktop apps need:
1. **Auto-update** — check GitHub Releases on startup, download + run installer silently
2. **Crash reporting** — capture unhandled exceptions, write minidump/log, offer to send report
3. **Crash log collection** — `logs/crash_<timestamp>.txt` with stack trace, version, OS info

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  App Startup    │────▶│  Check Updates   │────▶│  Download & Run  │
│  (frozen exe)   │     │  /api/updates/   │     │  New Installer   │
└─────────────────┘     │  check (GitHub)  │     └──────────────────┘
                        └──────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
            ┌───────────────┐       ┌───────────────┐
            │ Crash Handler │       │ Normal Run    │
            │ (sys.excepthook)       │ (main loop)   │
            └───────────────┘       └───────────────┘
                    │
                    ▼
         ┌────────────────────────┐
         │ Write crash_<ts>.txt   │
         │ Offer to send report   │
         └────────────────────────┘
```

## 1. Version & Update Check (Frozen Exe)

```python
# desktop_app.py (top-level, runs before webview)
import sys, os, json, urllib.request, tempfile, subprocess

APP_VERSION = "1.3.1"
GITHUB_REPO = "RekapalliVasudeva-MBU/aether-desktop"

def check_for_update() -> dict:
    """Returns {update_available: bool, latest: str, url: str, notes: str}"""
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "aether-desktop"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        latest = data["tag_name"].lstrip("v")
        # Semantic version compare
        def parse(v): return [int(x) for x in v.split(".")]
        if parse(latest) > parse(APP_VERSION):
            for asset in data.get("assets", []):
                if asset["name"].endswith(".exe"):
                    return {
                        "update_available": True,
                        "latest": latest,
                        "url": asset["browser_download_url"],
                        "notes": data.get("body", "")[:500],
                    }
        return {"update_available": False, "latest": APP_VERSION}
    except Exception as e:
        return {"update_available": False, "error": str(e)}

def download_and_run_installer(download_url: str) -> bool:
    """Download installer to temp, run silently, exit current app."""
    try:
        tmp = tempfile.mktemp(suffix=".exe", prefix="Aether-Setup-")
        urllib.request.urlretrieve(download_url, tmp)
        # Run installer silently (Inno Setup /VERYSILENT /SUPPRESSMSGBOXES)
        subprocess.Popen([tmp, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                         close_fds=True)
        return True
    except Exception:
        return False
```

## 2. Crash Handler (Unhandled Exception Capture)

```python
# Place at TOP of desktop_app.py, before any imports that might fail
import sys, traceback, datetime, platform, os

def _crash_handler(exc_type, exc_value, exc_tb):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Aether", "logs")
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, f"crash_{ts}.txt")
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Aether Crash Report\n")
        f.write(f"===================\n")
        f.write(f"Version: {APP_VERSION}\n")
        f.write(f"Time: {datetime.datetime.now().isoformat()}\n")
        f.write(f"Python: {sys.version}\n")
        f.write(f"OS: {platform.platform()} {platform.architecture()[0]}\n")
        f.write(f"Frozen: {getattr(sys, 'frozen', False)}\n")
        f.write(f"\nException: {exc_type.__name__}: {exc_value}\n\n")
        traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    
    # Try to show user-friendly dialog
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            f"Aether crashed unexpectedly.\n\nA crash report was saved to:\n{path}\n\n"
            "Would you like to open the log folder?",
            "Aether Crashed", 0x40 | 0x04  # MB_ICONERROR | MB_YESNO
        )
    except Exception:
        pass
    
    # Also print to stderr for any attached console
    traceback.print_exception(exc_type, exc_value, exc_tb)
    sys.exit(1)

sys.excepthook = _crash_handler
```

## 3. Backend Endpoints

```python
# desktop_app.py (FastAPI)
@app.get("/api/version")
async def api_version():
    return {
        "app_version": APP_VERSION,
        "home": str(config.AETHER_HOME),
        "python": sys.version.split()[0],
        "platform": platform.system() + " " + platform.release(),
        "github_repo": GITHUB_REPO,
    }

@app.get("/api/updates/check")
async def api_updates_check():
    result = check_for_update()
    result["current"] = APP_VERSION
    result["auto_upgrade"] = config.get_appearance().get("auto_upgrade", True)
    return JSONResponse(result)

@app.post("/api/updates/download")
async def api_updates_download(req: Request):
    body = await req.json()
    url = body.get("url", "").strip()
    if not url:
        return JSONResponse({"ok": False, "error": "url required"})
    try:
        tmp = tempfile.mktemp(suffix=".exe", prefix="Aether-Setup-")
        urllib.request.urlretrieve(url, tmp)
        return JSONResponse({"ok": True, "path": tmp})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})
```

## 4. UI Integration (Settings → About & Updates)

```html
<!-- desktop_ui/index.html snippet -->
<div class="settings-body" id="settings-updates">
  <h3>App Version: <span id="cur-ver">–</span></h3>
  <div id="update-status" class="hint">Checking…</div>
  <button class="btn" id="check-update" onclick="checkUpdate()">Check for Updates</button>
  <button class="btn ghost" id="apply-update" style="display:none" onclick="applyUpdate()">Download & Install</button>
  <div id="update-notes" class="hint" style="margin-top:8px"></div>
</div>

<script>
async function checkUpdate() {
  const r = await fetch(API+'/api/updates/check');
  const d = await r.json();
  document.getElementById('cur-ver').textContent = d.current;
  if (d.update_available) {
    document.getElementById('update-status').textContent = `Update available: v${d.latest}`;
    document.getElementById('apply-update').style.display = '';
    document.getElementById('update-notes').textContent = d.notes || '';
    window._updateUrl = d.url;
  } else {
    document.getElementById('update-status').textContent = `Up to date (v${d.current})`;
  }
}

async function applyUpdate() {
  const btn = document.getElementById('apply-update');
  btn.disabled = true; btn.textContent = 'Downloading…';
  const r = await fetch(API+'/api/updates/download', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({url: window._updateUrl})
  });
  const d = await r.json();
  if (d.ok) {
    btn.textContent = 'Installing…';
    // Run installer silently, then quit
    await fetch(API+'/api/updates/install', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({path: d.path})
    });
  } else {
    alert('Download failed: ' + d.error);
    btn.disabled = false; btn.textContent = 'Retry';
  }
}
</script>
```

## 5. Silent Installer Launch (Installer → App)

```python
# desktop_app.py — after download, before exit
@app.post("/api/updates/install")
async def api_updates_install(req: Request):
    body = await req.json()
    path = body.get("path", "")
    if not path or not os.path.isfile(path):
        return JSONResponse({"ok": False, "error": "invalid path"})
    try:
        # Inno Setup silent flags
        subprocess.Popen(
            [path, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"],
            close_fds=True
        )
        # Give installer time to start
        await asyncio.sleep(1.5)
        os._exit(0)  # hard exit current process
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})
```

## Key Files
- `references/auto-update-implementation.md` — full code with error handling
- `references/crash-handler-template.py` — drop-in excepthook
- `references/github-release-workflow.yml` — CI to build + publish signed releases

## Testing Checklist
- [ ] Fresh install → auto-update check works
- [ ] New version on GitHub → UI shows "Update available"
- [ ] Click "Install" → downloads, runs silently, new version launches
- [ ] Crash in frozen exe → `crash_<timestamp>.txt` written to `%LOCALAPPDATA%/Aether/logs/`
- [ ] Crash dialog offers to open log folder
- [ ] Auto-upgrade toggle in Settings respects user preference

## CI/CD (GitHub Actions)
```yaml
# .github/workflows/release.yml
on:
  push:
    tags: ['v*']
jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt pyinstaller
      - run: python build_aether.py
      - run: python make_installer.py
      - uses: softprops/action-gh-release@v1
        with:
          files: dist/Aether-Setup.exe
          generate_release_notes: true
```