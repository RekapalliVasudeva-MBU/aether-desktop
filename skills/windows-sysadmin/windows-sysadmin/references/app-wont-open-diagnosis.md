# Diagnosing "App Won't Open" — Single-Instance Launcher (verified recipe)

Context: Aether desktop app (FastAPI + pywebview, frozen with PyInstaller, installed
via Inno Setup to `C:\Users\valte\AppData\Local\Aether\Aether.exe`, launched by a
`.lnk` on the Desktop). Symptom: double-click does nothing.

## Step 1 — Is the process running? What port?
```bash
tasklist | findstr Aether.exe
netstat -ano | findstr :8732      # Aether's port
```
If a PID is listening on the port, the SERVER is alive. That does NOT mean the window is.

## Step 2 — Does that PID own a VISIBLE app window?
Run from `execute_code` / terminal with Python. A healthy app owns a visible window
titled with the app name. A dead window leaves only helper windows.

```python
import ctypes
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
EnumWindows = user32.EnumWindows
IsWindowVisible = user32.IsWindowVisible
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
target_pid = 31104   # from step 1
wins = []
def cb(hwnd, _):
    if not IsWindowVisible(hwnd):
        return True
    pid = ctypes.c_int()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == target_pid:
        length = GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowTextW(hwnd, buf, length + 1)
        wins.append((hwnd, buf.value))
    return True
EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(cb), 0)
for hwnd, t in wins:
    print(hwnd, repr(t))
# If you only see 'GDI+ Window (Aether.exe)' / 'Default IME' and NO real title ->
# the WebView window died; mutex is stale. This is the bug.
```

## Step 3 — Immediate unblock
Kill the stale PID so the port frees and a fresh launch works:
```bash
taskkill /PID 31104 /F
netstat -ano | findstr :8732     # should now be FREE
```
User can now double-click the `.lnk` and it opens.

## Step 4 — Fix the launcher (root cause)
The launcher's "other instance alive?" check must require BOTH:
- health port 200, AND
- a visible window owned by `<app>.exe` (scope by executable name via
  `GetModuleFileNameExW` from `psapi`, NOT a title string, NOT "any visible
  window from another PID" which false-positives on Explorer).

If server-up but no Aether window -> release mutex + take over.

## ctypes gotchas (cost real iteration time)
- `GetModuleFileNameExW` is in `ctypes.windll.psapi`, NOT kernel32.
- `SetForegroundWindow` from a non-foreground process is blocked -> use
  `AttachThreadInput` + `ShowWindow(hwnd, 9)` + `SetForegroundWindow` + detach.
- When editing a nested `cb` inside the launcher, an early `return True` placed
  after the work makes that work unreachable dead code. Re-read the patched block.
- Verify with an isolated test: extract the predicate, drive with synthetic windows
  (explorer-owned vs aether-owned visible). Assert True/False correctly. Lint passes
  even with dead code — only a behavioral test catches it.
