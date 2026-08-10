# Aether: branding rename + Settings backend wiring (verified this session)

## 1. Branding "Hermes One" / "Hermes Agent" -> "Aether"
The user grades the app against the Hermes One app daily and gets annoyed when
the app still shows the wrong name. The user-facing strings live in ONLY these
places — grep them all when renaming:

- `desktop_ui/index.html`:
  - `SETTINGS_NAV` array (the left Settings sub-nav labels) — `{id:'hermesone', label:'Hermes One'}` -> label `'Aether'`.
  - `renderSettingsHermesOne()` — the `<h3>` title + the `App`/`Desktop version`/`Home` card rows (`Hermes One Desktop` -> `Aether Desktop`).
  - `renderSettingsAbout()` — `<span>Hermes Agent</span>` -> `<span>Aether Engine</span>`, auto-upgrade hint text, footer `Hermes One Desktop v...` -> `Aether Desktop v...`.
  - `renderSettingsGeneral()` + `renderSettingsData()` — any "Hermes" hint text.
- `desktop_app.py`:
  - `APP_VERSION` constant (bump here, e.g. `"1.2.5"` -> `"1.2.6"`).
  - section comment labels (`# ---- about & updates (Settings > Hermes One...) ----`) — cosmetic, fix for cleanliness.
  - `/api/version` returns `config.AETHER_HOME` as `home` — that path is correct (`%APPDATA%/aether`); do NOT force it to "Aether" text, just ensure the KEY NAME shown in the UI label is "Aether".
- `aether/config.py`: `DEFAULT_CONFIG["appearance"]["auto_upgrade"]` comment (`auto-download Hermes One releases`) -> `Aether`.
- `aether_setup.iss`: `#define MyAppName "Aether"` (already correct) + `#define MyAppVersion "1.2.5"` -> bump to match `APP_VERSION`.
- The window title (`Aether — AI Agent + Personal RAG`) is already correct in `desktop_app.py` — leave it.

**Nav id stays `hermesone`** (internal dispatch key in `settingsGo`/`renderSettings`) — only the LABEL changes; renaming the id breaks the dispatcher.

## 2. Settings UI references a backend that may not exist
Class bug we hit: the Settings UI calls JS functions + REST routes that were
never implemented in the backend, so the buttons silently did nothing.

What the UI expects (grep `desktop_ui/index.html` for these and CONFIRM each has a
matching handler before claiming "Settings works"):
- `setAppearance(patch)` JS function -> POSTs to `/api/appearance`.
  - If `function setAppearance` is MISSING from index.html, the Appearance tab's
    theme/font/rounded switches throw `ReferenceError` on click. ADD it:
    ```js
    async function setAppearance(patch){
      try {
        await fetch(API+'/api/appearance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(patch)});
        applyAppearance();
      } catch(e){}
    }
    ```
- `/api/appearance` GET + POST -> `config.get_appearance()` / `config.set_appearance(patch)` in `aether/config.py`.
- `/api/backup/export` POST -> `config.export_backup()` (zips config.yaml, SOUL.md, USER.md, memory/, sessions/, skills/).
- `/api/backup/import` POST `{path}` -> `config.import_backup(src)`.
- `doExport()` / `doImport(input)` JS already exist in the UI — they just need the routes.

**Verification pattern (do this after ANY Settings UI edit):**
```bash
curl -s http://127.0.0.1:8732/api/appearance          # GET returns current theme
curl -s -X POST http://127.0.0.1:8732/api/appearance -H 'Content-Type: application/json' -d '{"theme":"tokyo_night"}'   # POST persists
curl -s -X POST http://127.0.0.1:8732/api/backup/export -H 'Content-Type: application/json' -d '{}'   # returns {ok,path}
```
Also: `grep -n "fetch(API+'/api/" desktop_ui/index.html` to enumerate every
route the UI calls, then `grep -n "@app.get(\"/api/..." desktop_app.py` to confirm
each has a handler. Mismatch = a broken Settings button.

## 3. Version bump checklist (per release)
1. `desktop_app.py` `APP_VERSION = "X.Y.Z"`.
2. `aether_setup.iss` `#define MyAppVersion "X.Y.Z"` (if rebuilding installer).
3. Rebuild + reinstall + headless-verify `/api/health` returns new version.
4. Commit source, then publish release (see `aether_frozen_exe.md` §4 — and the
   zip-publish note below for when Inno Setup is unavailable).

## 4. Publish when Inno Setup is NOT installed (portable zip path)
If `iscc`/`ISCC.exe` is absent (Inno Setup not on the machine), you CANNOT build
`Aether-Setup.exe`. Fall back to shipping the onedir folder as a zip:
```bash
powershell -NoProfile -Command "Compress-Archive -Path 'dist_build\Aether\*' -DestinationPath 'dist\Aether-X.Y.Z-portable.zip' -Force"
gh release create vX.Y.Z dist/Aether-X.Y.Z-portable.zip --title "Aether vX.Y.Z" --notes "..."
```
Gotchas:
- The zip is ~115 MB -> `gh release create` with the asset TIMES OUT the foreground
  call at 60s. Run it BACKGROUND with `notify_on_complete`, OR split: create
  release with no asset, then `gh release upload vX.Y.Z dist/...zip --clobber`.
- `gh release create` shows the release as a **DRAFT** during the upload, then
  flips to published when the upload completes. If the foreground call TIMES OUT
  (exit 124) you may have created a half-finished draft — DO NOT immediately run a
  second `gh release create` (that makes a SECOND duplicate draft with an
  "untagged-<hash>" URL). Instead: delete the draft first, then recreate once.
  ```bash
  gh release delete vX.Y.Z --yes        # removes the duplicate draft(s)
  gh release create vX.Y.Z dist/...zip --title "..." --notes "..."   # clean, one run
  ```
- The installed copy at `%LOCALAPPDATA%\Aether` is already the new version after
  you `cp -r dist_build/Aether/*` into it — the user does NOT need to redownload.
  State that clearly so they just open the shortcut.
