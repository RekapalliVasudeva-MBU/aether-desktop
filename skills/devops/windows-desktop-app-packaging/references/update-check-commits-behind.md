# Update Check Function with "Commits Behind" Feature

## Desktop App: `/api/updates/check` endpoint in `desktop_app.py`

The update check endpoint now returns `commits_behind` count so the UI can show "X commits behind" above the update button.

```python
@app.get("/api/updates/check")
async def api_updates_check():
    import json as _json
    import urllib.request as _urllib
    import subprocess
    
    ap = config.get_appearance()
    try:
        # 1. Check GitHub releases for latest version
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        rq = _urllib.Request(url, headers={"User-Agent": "aether-desktop"})
        with _urllib.urlopen(rq, timeout=12) as r:
            data = _json.loads(r.read().decode("utf-8"))
        latest = (data.get("tag_name") or "").lstrip("v")
        
        # 2. Get commits behind count
        commits_behind = 0
        try:
            # Get local commit hash
            local_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=os.path.dirname(os.path.dirname(__file__)),
                capture_output=True, text=True, timeout=5
            ).stdout.strip()
            
            # Get remote commit hash for latest tag
            remote_commit = subprocess.run(
                ["git", "ls-remote", f"https://github.com/{GITHUB_REPO}.git", f"refs/tags/v{latest}"],
                capture_output=True, text=True, timeout=10
            ).stdout.strip().split()[0] if subprocess.run(
                ["git", "ls-remote", f"https://github.com/{GITHUB_REPO}.git", f"refs/tags/v{latest}"],
                capture_output=True, text=True, timeout=10
            ).stdout.strip() else None
            
            if local_commit and remote_commit:
                # Count commits between local and remote
                result = subprocess.run(
                    ["git", "rev-list", "--count", f"{remote_commit}..{local_commit}"],
                    cwd=os.path.dirname(os.path.dirname(__file__)),
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    commits_behind = int(result.stdout.strip())
        except Exception:
            commits_behind = 0
        
        latest = (data.get("tag_name") or "").lstrip("v")
        return JSONResponse({
            "ok": True,
            "latest": latest,
            "current": APP_VERSION,
            "update_available": _version_gt(latest, APP_VERSION),
            "commits_behind": commits_behind,
            "download_url": f"https://github.com/{GITHUB_REPO}/releases/download/{data.get('tag_name')}/Aether-Setup.exe",
            "auto_upgrade": ap.get("auto_upgrade", True),
            "release_notes": data.get("body", ""),
        })
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e), "current": APP_VERSION})
```

## Website: `/api/app/update-check` endpoint in `server.py`

```python
@app.get("/api/app/update-check")
async def app_update_check(request: Request):
    """Check if a newer version of the desktop app is available."""
    CURRENT_VERSION = "1.3.1"
    
    # Get commits behind count
    commits_behind = 0
    try:
        import subprocess
        # Count commits from latest tag to HEAD
        result = subprocess.run(
            ["git", "rev-list", "--count", f"v{CURRENT_VERSION}..HEAD"],
            cwd=PROJECT_DIR,
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            commits_behind = int(result.stdout.strip())
    except Exception:
        commits_behind = 0
    
    LATEST_VERSION = CURRENT_VERSION
    UPDATE_AVAILABLE = False
    DOWNLOAD_URL = f"https://{CONFIG.get('cloudflare_tunnel_name', 'aether-rag')}.cfargotunnel.com/download/aether"
    CHANGELOG = "Fixed WebView2 auto-install crash; added RAG citations"
    
    return {
        "current_version": CURRENT_VERSION,
        "latest_version": LATEST_VERSION,
        "update_available": UPDATE_AVAILABLE,
        "commits_behind": commits_behind,
        "download_url": DOWNLOAD_URL,
        "changelog": CHANGELOG,
    }
```

## Desktop UI Update Display (`desktop_ui/index.html`)

```javascript
// In renderSettingsAbout():
<div class="addbar">
  <div class="kv" style="margin-bottom:8px">
    <span>Update available</span>
    <b style="color:${up.update_available?'var(--accent2)':'var(--muted)'}">
      ${up.update_available?('v'+up.latest):'Up to date'}
    </b>
  </div>
  <div class="kv" style="margin-bottom:8px">
    <span>Commits behind</span>
    <b style="color:${up.commits_behind>0?'var(--accent2)':'var(--muted)'}">
      ${up.commits_behind > 0 ? up.commits_behind + ' commits behind' : 'Up to date'}
    </b>
  </div>
  <button class="btn" onclick="checkUpdates()">Check for updates</button>
  <button class="btn ghost" id="dl-btn" style="display:${up.update_available?'inline-block':'none'}" onclick="downloadUpdate()">Download update</button>
```

## Version Comparison Helper

```python
def _version_gt(a: str, b: str) -> bool:
    def _parse(v):
        parts = []
        for x in (v or "").split("."):
            try:
                parts.append(int(x))
            except Exception:
                parts.append(0)
        return parts
    return _parse(a) > _parse(b)
```

## Integration Notes

1. **Desktop app** checks GitHub releases API + local git for commits behind
2. **Website** uses local git to count commits behind current tag
3. Both show "X commits behind" in UI above update button
3. When up to date: shows "0 commits behind" / "Up to date"
4. Download URL points to GitHub releases (desktop) or local tunnel (website)