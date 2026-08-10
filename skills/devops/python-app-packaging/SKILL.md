---
name: python-app-packaging
description: Freeze a Python desktop app into a native, double-click-to-install Windows installer using PyInstaller (bundle to .exe) + Inno Setup (wizard). Covers frozen-aware paths, ChromaDB/docling/pywebview pitfalls, per-user install without admin, and first-run data seeding. Use when the user wants to SHIP a Python desktop app to non-technical end users.
triggers:
  - "build an installer"
  - "make it a normal exe"
  - "so they just double-click to install"
  - "package a Python desktop app for Windows"
  - "replace the zip download with a setup wizard"
---

# Python App to Native Windows Installer

Freeze a Python desktop app into a real, double-click-to-install Windows
installer using **PyInstaller** (bundle the app into an `.exe`) + **Inno Setup**
(wrap it in a normal setup wizard). Use this whenever the user wants to *ship* a
Python desktop app to end users who are not developers.

## Principle (this user)
The deliverable must be a **normal installer wizard** the end user double-clicks
and that installs to Program Files with Start Menu + Desktop shortcuts. **Never
ship a `.zip` of source / loose Python files** — it confuses non-technical users
("what do I click to install?"). Simulate the user journey: download →
double-click → Next/Next/Install → launch from the Desktop shortcut.

## When to use
- "build an installer", "make it a normal exe", "so they just click to install"
- packaging a PySide/pywebview/Tkinter/Flask-desktop Python app for Windows
- replacing a confusing zip-of-source download

## Procedure
1. **Build in a clean venv** (not your active dev venv). A dev venv that also
   carries unrelated heavy packages (e.g. an agent framework) bloats the bundle
   to several GB. `python -m venv build_venv` then `pip install` only the app's
   deps + `pyinstaller`.
2. Add `app_paths.py` (see templates/app_paths.py). A frozen `.exe` does NOT live
   next to project source, and the user must WRITE data (DB, uploads, settings)
   **without admin rights**. The module sends read-only bundled assets to the exe
   dir and writable user data to `%LOCALAPPDATA%/<AppName>`, and seeds the latter
   from the bundle on first run. Import it from your entry point + main module
   and point all data paths at it.
3. Run the PyInstaller build via `build_exe.py` (templates/build_exe.py). It uses
   `--onedir --windowed`, bundles UI + sample docs + a prebuilt index, and
   post-syncs large nested dirs PyInstaller drops. Output: `dist/<AppName>/`.
4. **Test the frozen exe locally BEFORE building the installer.** Launch it in
   the background, redirect stdout to a log file, `sleep ~30s` (a 900 MB+ bundle
   boots slowly), then `curl` the app's API / open the UI and confirm it serves
   the seeded knowledge base. You WILL hit the failure modes in
   references/pyinstaller-pitfalls.md — read that file first.
5. Install Inno Setup (`is.exe` from jrsoftware.org), then run
   `iscc installer.iss` (templates/installer.iss) →
   `installer_out/ProjectRAG-Setup.exe`.
6. Point the website / download link at the new `ProjectRAG-Setup.exe`, not the zip.
7. End-to-end test: run the installer → verify the shortcut launches the app →
   confirm chat/query works against the seeded KB.

## Key references
- `references/pyinstaller-pitfalls.md` — every failure mode with the exact fix
  (chromadb dynamic imports incl. the hnswlib trap #8, docling pdf_resources,
  emoji UnicodeEncodeError, ChromaDB is_empty check, --add-data dropping nested
  dirs, --windowed traceback capture).
- `references/windows-installer-crashes.md` — 0xc0000142 (AV blocks `--onefile`
  `_MEI` unpack → use `--onedir`) + Inno bootloader `0xc0000005` (exclude
  torch/transformers/cv2 to shrink the payload) + rebuild lock cleanup. THE
  installer-specific crashes most likely to block shipping.
- `references/github-publish.md` — safe 2-repo publish: .gitignore traps
  (`nul` device file, ChromaDB binary dirs), **GitHub push failures (HTTP 408
  pack-timeout from `git add -A` sweeping build dirs + non-fast-forward
  divergence fix)**, pre-push staged secret scan, gh auth INCLUDING the
  cross-shell `gh auth` gap (PowerShell login invisible to the agent's MSYS bash
  — extract `gh config get` token → `export GH_TOKEN`).
- `templates/build_exe.py` — PyInstaller one-folder build scaffold (edit ENTRY/APP_NAME).
- `templates/app_paths.py` — frozen-aware path module (user data in %LOCALAPPDATA%).
- `templates/installer.iss` — Inno Setup script (per-user, no admin, WebView2 check).

## Pitfalls (quick index — full detail in references)
- `--windowed` + emoji `print()` → `UnicodeEncodeError`; reconfigure stdout to utf-8
  at the TOP of the entry module, before any import-time emoji print.
- Frozen `Path(__file__).parent` breaks writable paths → use `sys.executable`
  parent for assets + `%LOCALAPPDATA%` for user data.
- ChromaDB `is_empty` must `rglob` (UUID subdirs) or the app rebuilds the index.
- docling `pdf_resources` must be copied to `_internal/docling_parse/` post-build,
  or PDF parsing fails with "no existing pdf_resources_dir".
- chromadb dynamic imports → DO NOT use `--collect-submodules=chromadb` (it drags
  in `local_persistent_hnsw` → top-level `import hnswlib`, and there's no wheel/
  compiler here → fatal `No module named 'hnswlib'`). Use targeted
  `--hidden-import` (rust, telemetry.posthog, migrations.embeddings_queue) +
  `--exclude-module` the two hnsw segment files. Full recipe in references #3/#8.
- `--add-data` drops large nested data dirs → post-build `shutil.copytree` sync.
- `--windowed` = no console → always redirect the exe's stdout/stderr to a log
  file when testing so you can see tracebacks.
- **pywebview window icon does NOT take `icon=`**: older pywebview (pre-4.0,
  no `__version__`, `create_window` signature lacks `icon`) raises
  `TypeError: create_window() got an unexpected keyword argument 'icon'` and the
  app won't launch. FIX: do NOT pass `icon=` to `webview.create_window`. Set the
  EXE/taskbar icon at BUILD time instead — add `--icon=path/to/logo.ico` to the
  PyInstaller `sys.argv` list (PyInstaller embeds it; log shows "Copying icon to
  EXE"). For the in-window/favicon, add `<link rel="icon" href="/ui/logo.png">`
  to the bundled HTML and reference the image via the static-file route
  (`/ui/` mounts the UI dir). Also set `SetupIconFile=logo.ico` in the Inno
  `.iss` so the installer wizard + Start Menu shortcut carry the logo. Generage
  the `.ico` from the `.png`/`.svg` with Pillow
  (`img.save("logo.ico", sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])`).
  Verify the embedded icon after build: the exe bytes contain the ICO header
  (e.g. `b"ICON" in data`) and the taskbar/shortcut shows the mark.
- **Inno `SetupIconFile` must point at a REAL file (not blank).** If the `.iss` ships
  with `SetupIconFile=` (empty), the installer wizard + Start Menu shortcut get NO
  logo even though the bundled exe has one. Set `SetupIconFile=desktop\\ui\\logo.ico`
  (or wherever the `.ico` sits relative to the `.iss`). Also set
  `UninstallDisplayIcon={app}\\{#MyAppExe}` so the uninstall entry in Add/Remove
  Programs shows the app icon. Build the `.ico` with Pillow if only SVG/PNG exist
  (multi-size: 16/32/48/64/128/256). The logo mark itself: hand-draw a gradient
  rounded-rect + white glyph on a Pillow RGBA canvas (no cairosvg/SVG rasterizer
  needed) — match the site's brand colors so the desktop app + website + installer
  all look like the same product.

- **Inno Setup bootloader `0xc0000005` / `0xc0000142` on a LARGE onedir folder —
  the LZMA2 COMPRESSION (not the ML bloat) is the usual culprit. If a full Inno
  build exits 1 with NO log file created (bootloader never reached its main) and
  the event log shows `Exception code: 0xc0000005` for `Aether-Setup.exe`, FIRST
  try switching the Inno compression: change `Compression=lzma2/ultra64` +
  `SolidCompression=yes` to `Compression=zip` + `SolidCompression=no` in the `.iss`
  and rebuild. On ONE machine this single change turned a 0xc0000005 crash into a
  clean install — the LZMA2/ultra64 bootloader decompressor was what AV/Defender
  was faulting on, NOT the file count. Excluding torch/transformers/cv2 (below)
  SHRINKS the payload (921 MB → 135 MB) and is still recommended (smaller +
  faster download), but in this case it did NOT by itself clear the crash — only
  the `zip` compression did. Verify after: run the installed exe from the
  Inno-installed dir and confirm port + UI. Known-safe ML excludes for an app that
  only uses fastapi/webview/uvicorn/chromadb (no local ML): `torch`, `torchvision`,
  `torchaudio`, `transformers`, `tokenizers`, `safetensors`, `sentencepiece`,
  `huggingface_hub`, `timm`, `accelerate`, `cv2`, `onnxruntime`. Verify after:
  relaunch the frozen exe and hit its API + a RAG/docling query to confirm the
  exclusions didn't break a lazy import. Full diagnosis recipe in
  `references/windows-installer-crashes.md`.
- **A lingering `Aether.exe` locks `dist/<AppName>` → `PermissionError: [WinError 5]
  Access is denied` on rebuild.** PyInstaller can't overwrite a folder a still-
  running exe holds open (child PIDs too). Symptom: build fails at the COLLECT step
  with `Access is denied: '...dist_build\Aether'`. FIX: before every rebuild, kill
  ALL instances: `taskkill /F /IM Aether.exe` (and `Aether-Setup.exe`), confirm
  none remain with `tasklist | grep -i aether`, THEN build. Also note Windows
  "deferred delete" can leave a dir unlockable (`Device or resource busy`) until
  reboot — work around by building to a fresh output dir (e.g. `dist_build/` instead
  of `dist/`) rather than fighting the lock.
- **`--hidden-import pywebview` is WRONG (fails the build).** The package imports as
  `webview`, not `pywebview`. `pip show pywebview` may show stale metadata while
  `import webview` works. Use `--hidden-import webview`. (`pywebview` as a hidden
  import raises `ERROR: Hidden import 'pywebview' not found` and aborts the build.)

## This user's additional hard rules for packaging work
- **Preserve in-app options; never move them to config files.** If the app already
  had an in-UI control (PDF list, provider API-key paste field, add-PDF button),
  KEEP it. Do not refactor to "edit config.yaml" — the user explicitly rejects
  having to touch files by hand. Build new features as in-app UI, Hermes-desktop
  style (left sidebar with chat sessions, RAG-PDF panel, provider settings,
  capability toggle switches, gateway start/stop).
- **Verify the SHIPPED build through the app's own API/UI, not terminal.** Before
  reporting done, launch the frozen exe on a FREE port (set via an `AETHER_PORT`
  env var you add to `main()` so you can avoid the stale dev instance on the
  default port), then `curl` `/api/chat` with a real task (e.g. "build a calculator
  app") and confirm the agent used tools and wrote the file. The user tests
  features "inside the app", so a green terminal test is NOT sufficient.
- **Bundle the UI dir or the app serves 404 on `/ui/`.** With `--onefile`, add
  `--add-data "desktop_ui;desktop_ui"` (or the equivalent for your app) or the
  FastAPI `StaticFiles` mount finds nothing. Symptom: `/api/*` returns 200 but
  `/ui/` returns 404.
- **`main()` MUST `import os` if it reads `os.environ`.** A frozen exe crashed at
  boot with `NameError: name 'os' is not defined` because the entry module used
  `os.environ.get` but only imported `json/uuid/path`. Always import `os` at top.
- **Inno Setup not installed? build a self-contained installer instead of blocking.**
  Do NOT write a Python boot script and rename it to `.exe` — that produces a file
  with NO `MZ`/PE header and Windows refuses to run it with
  **"app can't run on your PC"** (this actually shipped once and had to be fixed).
  Instead, **PyInstaller-compile the installer itself** so the output is a genuine
  PE `.exe`. Write `installer_boot.py` (extracts payload from `sys._MEIPASS` to
  `%LOCALAPPDATA%/<AppName>`, winshell shortcuts, launches) and `make_installer.py`
  that builds a zlib payload `installer_payload.bin` (manifest `repr` + `\x00\x00` +
  blob) then runs `PyInstaller --onefile --windowed --add-data payload;. installer_boot.py`.
  CRITICAL: boot's `PAYLOAD_NAME` MUST equal the `--add-data` basename (a mismatch
  → FileNotFoundError at runtime). Full verified code in references/github-publish.md
  cross-link. Smoke-test by setting `LOCALAPPDATA` to a REAL Windows temp dir
  (NOT MSYS `/tmp`) and asserting the extracted `Aether.exe` has an `MZ` header.
- **Installer MUST be lock-proof (kill running app before overwrite).** If the user
  already launched the app (or an older install is running), `Aether.exe` holds
  `C:\Users\<user>\AppData\Local\Aether\Aether.exe` open and the installer dies with
  `PermissionError: [Errno 13] Permission denied` on write — this actually shipped and
  forced a re-download. FIX in `installer_boot.py`: before extracting, run
  `_kill_running_apps()` → `taskkill /F /IM aether.exe` (and `aether-setup.exe`,
  skipping `sys.executable` itself) then `time.sleep(1.5)` to release handles. Also
  wrap each `open(dp,"wb")` in `_write_with_retry(dp, chunk, attempts=5)` that re-runs
  the kill on `PermissionError` and retries. Verified: a locking `Aether.exe` in a
  sandbox `LOCALAPPDATA` + installer run → exit 0, file overwritten, extracted exe
  still a valid PE (`MZ`).
- **GitHub Releases is the PREFERRED host for large installers (>100 MB), but
  have a direct-serve FALLBACK.** `gh release create vX.Y.Z dist/X-Setup.exe
  --repo <owner>/<repo>` pushes the binary to `objects.githubusercontent.com`
  (fast CDN) — normally line-speed. BUT on a throttled/slow connection a 135 MB+
  upload can stall for 10+ min with zero bytes landed (the `gh` process stays
  alive, the draft release shows `assets: []`). When that happens, do NOT block
  the user waiting on it: serve the installer DIRECTLY from the web server instead
  of a 302 redirect. Change the download route to a `FileResponse` over the local
  `dist/X-Setup.exe` (already on disk, gitignored so it's never committed), e.g.
  `return FileResponse(PROJECT_DIR/"dist"/"X-Setup.exe", filename="X-Setup.exe",
  media_type="application/octet-stream")`. Keep the GitHub Releases URL as a
  secondary "mirror" string in the 404 body. The website download is then live
  IMMEDIATELY and independent of GitHub's upload speed. Verify with
  `curl -s -o /dev/null -w "%{http_code}" https://<site>/download/aether` → 200
  and `head -c2` of the stream == `MZ`. The GitHub asset upload can keep retrying
  in the background; once it lands, the 302-vs-direct choice no longer matters.
- **PREFER `--onedir` over `--onefile` for distributable desktop apps.** A `--onefile`
  build unpacks to a random `%TEMP%\_MEIxxxx` folder on EVERY launch; antivirus
  often blocks/quarantines those unpacked DLLs → the exe dies at startup with
  **`0xc0000142` ("application was unable to start correctly")** and NO SideBySide
  event in the log (clean Python exit or AV kill, not a missing-VC++ fault). The
  fix that actually works: build `--onedir` (files sit next to the exe, no runtime
  temp-unpack) and wrap THAT folder in the installer. Verified: an `--onedir`
  `Aether.exe` launches and binds its port cleanly; a `--onefile` of the same code
  is the classic 0xc0000142 trigger. If you must ship a single `.exe` and accept
  the AV risk, use `--onefile` but tell the user to add a Defender exclusion.
  Build `python -m PyInstaller --onefile --windowed --add-data "desktop_ui;desktop_ui"
  build_aether.py`. Symptom if you forget `--add-data`: `/api/*` → 200 but `/ui/` →
  404. The single `.exe` is then wrapped by the self-contained installer above.
- **Never kill a process without consent in a blind destructive combo.** Restarting
  the website server the user asked you to "push to" is in scope, but do it as a
  targeted `taskkill /PID <n> /F` (one known PID), not a `pkill`/`netstat`/`taskkill`
  sweep. Stale ngrok agents orphaned from a killed server hold the static domain
  (`ERR_NGROK_334 "already online"`) — kill the orphaned `ngrok.exe` PIDs, wait a
  cooldown (~45-60s for ngrok cloud to release), then relaunch the server so it
  claims the tunnel. Concrete recovery loop that worked:
  1. `netstat -ano | grep ":8000 "` → kill that PID (the server).
  2. `tasklist | grep -i ngrok` → `taskkill /PID <ngrok_pids> /F` (orphaned agents).
  3. Wait 45-60s.
  4. Relaunch `python server.py` (background) and watch for the
     `Public URL (share this): https://...` line in startup output — that confirms
     the tunnel was claimed. If you still get `ERR_NGROK_334`, a second ngrok.exe
     survived; repeat steps 2-3.
- **Publish to GitHub SAFELY (private, no secret leak).** Full recipe in
  `references/github-publish.md` — covers 2-repo split, `.gitignore` traps
  (`nul` device file breaks `git add`; ChromaDB binary dirs + `*.log` must be
  ignored), and a staged-files secret scan before every push. User hard rule:
  repos MUST be private; the assistant creates them and the user flips public
  manually after review. `gh` must be authenticated (`gh auth login`) first —
  the agent cannot create/push repos unauthenticated.
- **NEVER `git add -A` a build tree — it causes push failure 408 + repo bloat.**
  PyInstaller outputs (`dist/`, `dist_build/`, `build_aether/`), Inno outputs
  (`*.exe`, `*.iss`), and runtime DBs (`deploy/`, `rag_vector_db/`) MUST be in
  `.gitignore` BEFORE the first commit. `git add -A` in a repo that also contains
  these folders commits 3000+ files (incl. 94 MB `aether_test2.exe`, 36 MB
  `build_aether/Aether/Aether.exe`, 8 MB `chroma.sqlite3`) and the resulting push
  dies with `HTTP 408 the remote end hung up unexpectedly` (pack upload timeout).
  After commit, sanity-check: `git ls-files | wc -l` should be ~100 (source only),
  NOT 3000+. If it's huge, `git rm -r --cached` those dirs + `.gitignore` them +
  amend. Also: if `git push` says "failed to push some refs" with no detail, the
  branch diverged from the remote — `git fetch origin && git rebase origin/main`
  then push (non-fast-forward, not a hook). Full recipe in
  `references/github-publish.md`.
  After any build the user double-clicks, run
  `python -c "print(open('dist/X-Setup.exe','rb').read(2)==b'MZ')"` → must be True.
  A `.py` renamed to `.exe` (or any non-PE) prints False and MUST be rebuilt.
  This one check would have caught the "app can't run on your PC" incident:
  `make_installer.py` had written a Python *script* renamed to `.exe`, which has
  no `MZ` header. The fix: PyInstaller-compile the installer (see the
  self-contained-installer rule above), don't rename a script.
