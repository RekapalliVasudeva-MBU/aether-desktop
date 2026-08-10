# Aether frozen-exe: build, verify, and the MCP-Windows-pipe fix

Condensed, verified patterns for the Aether downloadable desktop app (frozen
PyInstaller bundle running a FastAPI server + native pywebview window).

## 1. Verify through the REAL bundled exe (not the MSYS shim)
The agent terminal's `python` is the uv shim. Its subprocess-pipe behavior
DIFFERS from the frozen exe — a fix that works under the shim can still fail in
the exe, and vice-versa. To prove a fix, run it through the actual `Aether.exe`.

Add an `AETHER_HEADLESS=1` guard to `main()` (serve, no WebView2):
```python
if os.environ.get("AETHER_HEADLESS") == "1":
    print("[desktop] headless — server only, no window")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    return
```
Launch + probe (the exe uses real Windows Python, so this is authoritative):
```bash
cd "$LOCALAPPDATA/Aether" && ./Aether.exe        # background
sleep 6
curl -s http://127.0.0.1:8732/api/health
curl -s -X POST http://127.0.0.1:8732/api/mcp/test -H 'Content-Type: application/json' -d '{"name":"x"}'
```

## 2. MCP stdio transport on Windows — THE fix (Errno 22)
Symptom: `Test Connection` against a stdio MCP server fails with
`[Errno 22] Invalid argument`.

What does NOT work on this machine's Python (frozen OR shim):
- `Popen(..., text=True, bufsize=1)` + `stdin.write` + `stdin.flush()` -> `flush()` raises Errno 22.
- raw `os.write(self.proc.stdin.fileno(), bytes)` -> `os.write` raises Errno 22.
- `text=True` + write + flush (default buf) -> hangs/deadlocks in the frozen exe.

What WORKS (verified):
```python
self.proc = subprocess.Popen(
    [cmd, *args], stdin=PIPE, stdout=PIPE, stderr=DEVNULL, bufsize=0,
)  # unbuffered binary
# send — NO flush() (unbuffered, sent immediately):
self.proc.stdin.write((json.dumps(msg) + "\n").encode("utf-8"))
# recv — byte-by-byte until newline:
buf = b""
while True:
    ch = self.proc.stdout.read(1)
    if not ch or ch == b"\n":
        break
    buf += ch
resp = json.loads(buf.decode("utf-8"))
```
ALSO add a hard read timeout so a dead/misbehaving server can NEVER hang the UI
or test forever:
```python
import select
rlist, _, _ = select.select([self.proc.stdout], [], [], 10)
if not rlist:
    raise TimeoutError("MCP server did not respond within 10s")
```
Keep a `threading.Lock` around request->response so a notification (no response)
and a request don't interleave.

CAVEAT: even with the working transport, MCP **stdio** spawned by the frozen exe
can still hang when `command` is a re-execing shim (e.g. `python`) that breaks the
inherited pipe fds. Prefer **HTTP MCP** servers, or pass an ABSOLUTE executable
path. HTTP transport (`requests.post` to a URL) is fully solid. This is the one
item that stayed "verified in normal Python, unstable in the frozen bundle" — ship
HTTP-MCP as the recommended path.

## 3. Startup crash that masquerades as "backend won't start"
Symptom: app shows "could not start its backend server / local API did not become
ready in time" even though port 8732 is free and nothing blocks it.
`tasklist /v` shows `Unhandled exception in script`.

Root cause we hit: a refactor moved RAG PDF-ingest into a background thread but
referenced `_threading` BEFORE `import threading as _threading` ran -> `NameError`
killed the app before `uvicorn.run` was ever reached; the readiness probe then
timed out and showed the fail box.

Fix:
- `import threading as _threading` at the TOP of `main()`, not mid-function.
- Start the server thread FIRST, then offload heavy init (RAG ingest, model
  warmup) to a background thread so it can never delay binding.
- Extend the health probe to ~45s for cold/first-run headroom.
- Write a startup log to `%LOCALAPPDATA%/Aether/aether_startup.log` (a
  "starting uvicorn on PORT" line + any `uvicorn.run` traceback) so a future
  failure is diagnosable instead of a silent crash.
- Make the fail-box message accurate (no antivirus hint unless relevant — the
  user has none).

## 4. Publishing the ~181MB installer via `gh`
`gh release create vX.Y.Z dist/Aether-Setup.exe ...` with a 181MB asset TIMES OUT
(120-200s) on upload. Do it in two steps:
```bash
gh release create vX.Y.Z --title "Aether vX.Y.Z" --notes "..."   # no asset
gh release upload vX.Y.Z dist/Aether-Setup.exe --clobber        # 600s timeout
```
Update `project_rag/server.py`'s download redirect to the new tag in the same cycle.

## 5. FROZEN-EXE `isatty`/`sys.stdout=None` CRASH (the real "backend won't start")
In a PyInstaller-frozen exe `sys.stdout` AND `sys.stderr` are `None`. Uvicorn's
default formatter (`uvicorn.logging.DefaultFormatter`) calls `self.stream.isatty()`
-> `AttributeError: 'NoneType' object has no attribute 'isatty'` ->
`ValueError: Unable to configure formatter 'default'` -> `uvicorn.run` raises ->
server never binds -> the 45s probe times out -> "API did not become ready in time".
This was the actual root cause behind the v1.2.x launch failures (the NameError in
§3 was a second, separate regression on top).

FIX (apply at the very TOP of `main()`, before `uvicorn.run` is ever reached):
```python
try:
    _logdir = Path(os.environ.get("LOCALAPPDATA", "")) / "Aether"
    _logdir.mkdir(parents=True, exist_ok=True)
    _logfile = open(_logdir / "aether_stdout.log", "a", encoding="utf-8", buffering=1)
    if sys.stdout is None: sys.stdout = _logfile
    if sys.stderr is None: sys.stderr = _logfile
except Exception:
    pass
```
After this patch the exe starts in ~1-3s. Verify: `AETHER_HEADLESS=1` launch +
`curl /api/health` returns `{"ok":true,"version":"X.Y.Z"}` with NO crash in
`aether_startup.log`.

## 6. Publish portable zip when Inno Setup is absent
If `iscc`/`ISCC.exe` is not installed you cannot build `Aether-Setup.exe`. Zip the
onedir (`Compress-Archive dist_build\Aether\*`) and `gh release create` with that
asset. The asset (~115 MB) times out a foreground call — run it backgrounded OR
split into create-then-upload. `gh release create` shows a DRAFT during upload and
publishes on completion; if the foreground call times out (exit 124) you may have
a half-finished draft — delete it (`gh release delete vX.Y.Z --yes`) before
recreating, or you get a duplicate "untagged-<hash>" draft. The installed copy at
`%LOCALAPPDATA%\Aether` is already the new version after `cp -r dist_build/Aether/*`
— the user just opens the shortcut. (Full detail in `references/aether_settings_branding.md` §4.)

