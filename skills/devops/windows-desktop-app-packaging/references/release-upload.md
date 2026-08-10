# Releasing a new Aether version (GitHub Releases, large asset)

The installer (`Aether-Setup.exe`) is ~180 MB. Publishing it has two gotchas
that waste a full rebuild if you hit them mid-session.

## 1. Upload in BACKGROUND, never foreground

`gh release create <tag> <file> -R <repo> ...` uploads the file inline. On a
slow link a 180 MB upload takes **5–7 minutes**. The Hermes `terminal` tool
clamps a foreground call at 60s, so a foreground run **silently times out
(exit 124) and leaves a half-made release** (tag exists, asset missing).

ALWAYS launch the upload with `terminal(background=true,
notify_on_complete=true)` and `process(action='wait')` / poll for completion:

```bash
cd "C:/Users/valte/aether"
gh release create v1.1.0 "dist/Aether-Setup.exe" \
  -R RekapalliVasudeva-MBU/aether-desktop \
  -t "Aether v1.1.0 — native desktop shell" \
  -n "Hermes-One-style native app: per-item skill/tool/MCP toggles, providers panel, memory editor, persona editor, RAG PDF drop-in folder, Telegram gateway setup, fixed app icon."
```

`gh release upload <tag> <file>` has the same constraint — background it too.
After it exits (exit 0, prints the release URL), verify the asset is present:
`gh release view -R <repo> --json assets`.

## 2. Repoint the website download redirect to the new tag

The public site serves the installer as a **302 redirect to a fixed release
tag** (so the binary never burns the tunnel's bandwidth). After you publish a
new tag, the redirect still points at the OLD tag until you update it — users
keep downloading the previous build.

In `C:/Users/valte/project_rag/server.py`, the `/download/aether` route:

```python
return RedirectResponse(
    "https://github.com/RekapalliVasudeva-MBU/aether-desktop/releases/download/v1.0.1/Aether-Setup.exe",
    status_code=302,
)
```

Bump `v1.0.1` → the new tag (e.g. `v1.1.0`). Then restart the website server
(`taskkill` the `server.py` process + relaunch, or it picks up on next boot via
the self-heal script). Verify: `curl -sI <site>/download/aether` → `302` and
`Location:` ends in the new tag.

## 3. Version checklist (do in order)

1. Rebuild frozen exe (`build_aether.py`, --icon set) + installer (`make_installer.py`).
2. `gh release create` (BACKGROUND) with the new tag + installer asset.
3. Update `/download/aether` redirect tag in `server.py`; restart website.
4. Reinstall to `%LOCALAPPDATA%\Aether` (rm old dir, cp `dist_build/Aether/.`);
   launch via `terminal(background=true)`; poll port + `/ui/` → 200.
5. Commit + push source to `aether-desktop` main.
