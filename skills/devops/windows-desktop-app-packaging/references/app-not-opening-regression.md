# "App not opening" regression recipe (Aether desktop)

## Symptom
User double-clicks the desktop `.lnk`; nothing appears — no window, no browser
tab, no error. Task Manager may or may not show an `Aether.exe`.

## Root-cause classes (verify in order)
1. **Orphan holds 8732 + silent-exit guard (v1.1.1 bug).** If `_port_in_use(8732)`
   led to `return` (silent exit), a fresh double-click with any zombie on 8732
   exits immediately -> nothing visible. The port is still served by the zombie,
   so new endpoints 404 against old code.
   - Fix: free-port fallback in `main()` (bind `127.0.0.1:0`, use that port).
   - Confirm in a test: start a dummy `socket.bind(('127.0.0.1',8732))`, then
     launch the exe -> expect the native window to open on a different port and
     `tasklist | grep Aether.exe` count == 1.
2. **Stale process shadowing** (see main SKILL.md): `netstat -ano | findstr :8732`
   -> PID -> `taskkill /PID <pid> /F`; relaunch clean.
3. **Blank/iconless but working**: `.lnk` `IconFilename` points at a missing
   `logo.ico` (PyInstaller embeds but doesn't copy it). App opens fine; only the
   logo is blank. Fix: copy `logo.ico` next to the exe at runtime + re-point .lnk.

## How this was reproduced + verified (v1.2.0)
- Started orphan: `python -c "import socket;s=socket.socket();s.bind(('127.0.0.1',8732));s.listen(1);import time;time.sleep(45)"`
- Launched installed exe: `./Aether.exe` in `terminal(background=true)`.
- Read `/tmp/fb2.log` + `tasklist | grep -i Aether.exe | wc -l` -> got **1** native
  window with the new free-port fallback (old code logged "already running" and
  spawned 0 windows).
- UI check: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8732/ui/` -> 200.

## Gotcha: testing exit codes
`timeout 15 ./Aether.exe` returning **124** means the exe launched and timeout
killed it -- that is proof it ran, NOT a crash. Don't treat 124 as failure.
