# Import-time crash transcript — pathlib backport shadowing stdlib

Real output captured when `hermes --version` was dead on a Windows install
(Python 3.11.15, venv at `C:\Users\<user>\AppData\Local\hermes\hermes-agent\venv`).

## Symptom (every command, including `hermes doctor` and `python -m pip`)
```
Error processing line 1 of ...\venv\Lib\site-packages\__editable__.hermes_agent-0.17.0.pth:

  Traceback (most recent call last):
    File "<frozen site>", line 195, in addpackage
    File "<string>", line 1, in <module>
    File "...\venv\Lib\site-packages\__editable___hermes_agent_0_17_0_finder.py", line 7, in <module>
      from pathlib import Path
    File "...\venv\Lib\site-packages\pathlib.py", line 10, in <module>
      from collections import Sequence
  ImportError: cannot import name 'Sequence' from 'collections'
  (C:\Users\valte\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none\Lib\collections\__init__.py)

Remainder of file ignored
... (repeats for rag_system_production .pth too) ...

Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "...\venv\Scripts\hermes.exe\__main__.py", line 2, in <module>
    from pathlib import Path
  File "...\venv\Lib\site-packages\pathlib.py", line 10, in <module>
    from collections import Sequence
ImportError: cannot import name 'Sequence' from 'collections'
```

## Diagnosis that pinned it
- The traceback names the failing import: `from collections import Sequence`.
- Same error fires from `hermes.exe`, `hermes doctor`, AND `python -m pip` —
  so the breakage is at interpreter/site startup, before any Hermes code runs.
- The offending file: `venv/Lib/site-packages/pathlib.py` line 10.
- Owning package confirmed:
  `ls venv/Lib/site-packages/` → `pathlib.py` + `pathlib-1.0.1.dist-info`.
- `python -m pip uninstall pathlib` ALSO crashes (pip imports pathlib at
  startup, which is the shadowed one) → must delete by hand.

## Fix that worked
```bash
cd venv/Lib/site-packages
rm -rf pathlib.py pathlib-1.0.1.dist-info
# verify:
cd ../../..        # back to hermes-agent/
./venv/Scripts/hermes.exe --version
# -> Hermes Agent v0.17.0 (2026.6.19) ... (no crash; update then proceeded)
```

## Why it's safe to remove
`pathlib` is Python 3.4+ stdlib. The PyPI `pathlib 1.0.1` is a backport only
needed on Python 2 / <3.4. Hermes requires 3.10+, so it uses stdlib `pathlib`
exclusively. The standalone package is dead weight that breaks 3.10+.

## Context of capture
Hit during a self-update session (2026-07-09): `hermes` was dead, so the
normal `hermes update` couldn't run. After removing the shadow, the git-checkout
update to `v2026.7.7.2` (v0.18.2) succeeded. See SKILL.md for the full update
sequence and the gateway-restart pitfall.
