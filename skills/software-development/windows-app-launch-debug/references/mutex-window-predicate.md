# Mutex / Window Predicate — working reference

Exact ctypes logic for a single-instance Windows app launcher. Verified against
the Aether "won't open" bug (server alive on :8732 but WebView window dead;
second launch silently exited).

## 1. "Does another instance have a usable visible window?" predicate

```python
def _other_instance_has_window() -> bool:
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        EnumWindows = user32.EnumWindows
        IsWindowVisible = user32.IsWindowVisible
        GetWindowThreadProcessId = user32.GetWindowThreadProcessId
        my_pid = kernel32.GetCurrentProcessId()
        found = []

        def cb(hwnd, _):
            if not IsWindowVisible(hwnd):
                return True
            pid = ctypes.c_int()
            GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if not pid.value or pid.value == my_pid:
                return True
            # Only count windows owned by an Aether.exe process.
            buf = ctypes.create_unicode_buffer(1024)
            hproc = kernel32.OpenProcess(0x0400, False, pid.value)  # PROCESS_QUERY_INFORMATION
            is_aether = False
            if hproc:
                try:
                    psapi = ctypes.windll.psapi
                    psapi.GetModuleFileNameExW(hproc, 0, buf, 1024)
                    exe = buf.value.lower()
                    is_aether = exe.endswith("aether.exe")
                except Exception:
                    is_aether = False
                kernel32.CloseHandle(hproc)
            if not is_aether:
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                tbuf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, tbuf, length + 1)
                t = tbuf.value
                if t and "GDI+ Window" not in t and "Default IME" not in t:
                    found.append(hwnd)
            return True

        EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(cb), 0)
        return len(found) > 0
    except Exception:
        return False
```

## 2. "Is the other instance alive AND usable?" (drives take-over decision)

```python
def _other_instance_alive() -> bool:
    import urllib.request
    port = int(os.environ.get("AETHER_PORT", "8732"))
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1.5) as r:
            if r.status != 200:
                return False
    except Exception:
        return False
    return _other_instance_has_window()   # <-- REQUIRE a visible window, not just the port
```

If `already_running and not _other_instance_alive()` → release mutex, `already_running = False`, start fresh.

## 3. Focus-raise an existing instance (when it IS alive)

Windows refuses `SetForegroundWindow` from a non-foreground process unless you
attach to the foreground thread's input first.

```python
def _focus_existing_window():
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        EnumWindows = user32.EnumWindows
        IsWindowVisible = user32.IsWindowVisible
        GetWindowThreadProcessId = user32.GetWindowThreadProcessId
        ShowWindow = user32.ShowWindow
        SetForegroundWindow = user32.SetForegroundWindow
        SW_RESTORE = 9
        my_pid = kernel32.GetCurrentProcessId()
        targets = []
        def cb(hwnd, _):
            if not IsWindowVisible(hwnd): return True
            pid = ctypes.c_int(); GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value and pid.value != my_pid:
                ln = user32.GetWindowTextLengthW(hwnd)
                if ln > 0:
                    b = ctypes.create_unicode_buffer(ln + 1)
                    user32.GetWindowTextW(hwnd, b, ln + 1)
                    t = b.value
                    if t and "GDI+ Window" not in t and "Default IME" not in t:
                        targets.append(hwnd)
            return True
        EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(cb), 0)
        if not targets: return
        hwnd = targets[0]
        fg = user32.GetForegroundWindow()
        fg_thread = user32.GetWindowThreadProcessId(fg, ctypes.byref(ctypes.c_int())) if fg else 0
        my_thread = kernel32.GetCurrentThreadId()
        target_thread = GetWindowThreadProcessId(hwnd, ctypes.byref(ctypes.c_int()))
        try:
            if fg_thread and fg_thread != my_thread:
                user32.AttachThreadInput(my_thread, fg_thread, True)
            if target_thread and target_thread != my_thread:
                user32.AttachThreadInput(my_thread, target_thread, True)
        except Exception: pass
        try:
            ShowWindow(hwnd, SW_RESTORE)
            SetForegroundWindow(hwnd)
        finally:
            try:
                if fg_thread and fg_thread != my_thread:
                    user32.AttachThreadInput(my_thread, fg_thread, False)
                if target_thread and target_thread != my_thread:
                    user32.AttachThreadInput(my_thread, target_thread, False)
            except Exception: pass
    except Exception: pass
```

## Pitfalls actually hit this session

- `GetModuleFileNameExW` is in `ctypes.windll.psapi`, NOT `kernel32`. A
  `kernel32.GetModuleFileNameExW = ...` assignment throws `AttributeError` inside
  `try` and silently breaks the predicate (always returns "no window").
- A patch with wrong indentation nested `found.append(hwnd)` UNDER
  `if not is_aether: return True`, making it unreachable dead code → predicate
  always False. Static `grep` for reachability catches this; an unwinnable ctypes
  mock harness will NOT (byref CArgObject mocking fails).
- Mocking `EnumWindows(cb)` with a fake `cb` that receives `byref(pid)` is a trap:
  your mock gets a `CArgObject`, not an int. Verify headlessly only the cases that
  need no GUI (dead-instance → False); for the window-present case rely on a real
  frozen build + user relaunch.
