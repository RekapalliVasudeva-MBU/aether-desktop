---
name: hermes-cli-repair
description: "Diagnose and repair a Hermes Agent install when the CLI won't even start (import-time crashes from shadowed stdlib modules, broken venv) and perform the Windows git-checkout self-update safely without breaking the gateway."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
---

# Hermes CLI Repair & Self-Update

Use when `hermes` (or `hermes doctor`, `python -m pip`) crashes at import time before doing anything, OR when the user asks to update Hermes and the normal `hermes update` flow is unavailable/broken.

**Overlap note:** the happy-path Windows update procedure also lives in the bundled `hermes-agent` skill (`references/windows-update-procedure.md`). This skill covers the *repair* class — when the CLI is dead on arrival and the standard update can't run — plus the git-checkout update with the stray-file rescue. Keep both; the curator consolidates.

## Signal 1 — ImportError at import time (CLI won't start)
Symptom: every `hermes` call prints
`Error processing line 1 of .../site-packages/__editable__.hermes_agent-*.pth`
then `ImportError: cannot import name 'Sequence' from 'collections'`.

### Root cause (most common real case)
A **top-level module in the venv's `site-packages` shadows a stdlib module**.
The flagship case: the `pathlib` PyPI backport (package `pathlib-1.0.1`) drops a
`pathlib.py` into site-packages that does `from collections import Sequence`
— removed in Python 3.10+. It is NOT a Hermes dependency (Hermes uses stdlib
`pathlib`), so it is always safe to remove.

### Diagnostic (don't guess — read the first traceback)
1. The `.pth` loader error names the broken file and the failing import.
2. The chain points at `site-packages/pathlib.py` line ~10 `from collections import Sequence`.
3. Confirm it's foreign: grep Hermes requirements — no standalone `pathlib` dep.
4. Confirm it's a separately-installed package:
   `ls -d venv/Lib/site-packages/pathlib*`

### Fix — remove by hand (pip is also broken by the shadow)
The shadowed `pathlib` breaks pip's own entrypoint, so `python -m pip uninstall pathlib`
crashes with the SAME ImportError. Delete the files directly:
```bash
cd "<HERMES>/hermes-agent/venv/Lib/site-packages"
rm -rf pathlib.py pathlib-1.0.1.dist-info
# POSIX equivalent: rm -rf pathlib.py pathlib-*.dist-info
```
Verify:
```bash
cd "<HERMES>/hermes-agent"
./venv/Scripts/hermes.exe --version    # Windows
# ./venv/bin/hermes --version          # POSIX
```
If it prints a version instead of an ImportError, the blocker is cleared.

Generic form of this class: ANY `ImportError`/`AttributeError` at import that
names a stdlib module means a same-named top-level file in site-packages is
shadowing it. Find the owning `*.dist-info`, confirm it's not a real dep,
remove the file + dist-info, re-verify.

## Signal 2 — Updating Hermes on Windows (git-checkout method)
Do NOT use `hermes update` if the CLI was broken, and do NOT stop the gateway yourself.

1. Source checkout: `C:\Users\<user>\AppData\Local\hermes\hermes-agent` (or `$HERMES_HOME/hermes-agent`).
2. `git stash` — preserve any local source mods.
3. `git fetch origin`
4. **Rescue stray root-level artifacts BEFORE cleaning** — they are untracked and `git clean -fd` would wipe them. Move files like `*.md` notes, `*.html`, scratch `*.py`, `*.orig`, and `nul` to `AppData\Local\hermes\update_backup\`.
5. `git clean -fd` — drops desktop-app source etc. that the new tag restores (safe).
6. `git checkout v2026.7.7.2` — pick the **newest stable tag** from `git tag --sort=-v:refname | head`. Prefer a release tag over `main` unless the user explicitly wants bleeding edge.
7. `./venv/Scripts/python.exe -m pip install -e . --force-reinstall --no-cache-dir`
8. Verify: `./venv/Scripts/hermes.exe --version`

### Pitfall: checkout aborts on untracked files
`error: The following untracked working tree files would be overwritten by checkout`
→ rescue the stray non-repo files (step 4), then `git clean -fd` the rest, then retry the checkout. Do NOT force-checkout blindly over them.

### Pitfall: gateway still runs old code
After update, the **running gateway holds old code in memory** — restarting it is the USER's call. Do not restart the gateway autonomously. Tell the user to send `/restart` (gateway) or restart the service. New `hermes` CLI invocations already use the new version.

### Pitfall: version still reports "behind"
`hermes --version` may say "N commits behind" after a release-tag checkout — that's unreleased `main`. Confirm success via `git describe --tags` and `hermes_cli/__init__.py` `__version__`, both matching the target tag.

## Verification checklist
- [ ] `hermes --version` prints the new version (not an ImportError)
- [ ] `hermes doctor` runs; Python env + SSL show ✓
- [ ] `git describe --tags` matches intended tag
- [ ] Gateway restart deferred to user

## References
- `references/import-crash-transcript.md` — real error output for the pathlib backport case.
