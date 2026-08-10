# Single-instance native window (Windows mutex) — Aether v1.2.1 recipe

## Why a mutex (not port-check, not browser fallback)

Three prior attempts all failed for this user:

1. `if _port_in_use(): webbrowser.open(url); return` — popped a **browser tab**
   on every second launch (user rejected: "u again fixed it to local host website").
2. `if _port_in_use(): return` (silent exit) — if any orphan held 8732, a fresh
   double-click showed **nothing** ("app not opening").
3. `if _port_in_use(): bind_free_port(); open_second_webview()` — two
   `Aether.exe` processes both call `webview.create_window` from the same install
   path -> **WebView2 conflict** -> second window fails -> browser fallback ->
   `http://127.0.0.1:65338/ui/` loop (the bug actually reported).

**Only one design is robust: a Windows named mutex so exactly one process and
exactly one WebView2 ever exist.** Second launch focuses the existing window.

## Full `main()` (drop-in)

```python
import ctypes, threading as _threading, time

def main():
    config.ensure_persona_files()
    try:
        import shutil
        shutil.copyfile(UI_DIR / "logo.ico", Path(sys.executable).parent / "logo.ico")
    except Exception:
        pass
    try:
        res = config.index_pdf_watch_dir()
        if res.get("added"):
            print(f"[rag] auto-ingested {res['added']} PDF(s)")
    except Exception as e:
        print(f"[rag] watch-dir ingest skipped: {e}")

    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, 0, "Global\\AetherSingleInstanceMutex")
    already_running = (kernel32.GetLastError() == 183)  # ERROR_ALREADY_EXISTS

    def _focus_existing_window():
        user32 = ctypes.windll.user32
        target_title = "Aether — AI Agent + Personal RAG"
        def cb(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if target_title in buf.value:
                user32.ShowWindow(hwnd, 9)          # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
                return False
            return True
        user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(cb), 0)

    if already_running:
        print("[desktop] already running — focusing it")
        _focus_existing_window()
        kernel32.ReleaseMutex(mutex)
        return

    import uvicorn
    port = int(os.environ.get("AETHER_PORT", "8732"))
    url = f"http://127.0.0.1:{port}/ui/"
    _threading.Thread(target=lambda: uvicorn.run(
        app, host="127.0.0.1", port=port, log_level="warning"), daemon=True).start()
    time.sleep(1.5)

    started = False
    try:
        import webview
        webview.create_window("Aether — AI Agent + Personal RAG", url=url,
                              width=1280, height=840,
                              icon=str(Path(sys.executable).parent / "logo.ico"),
                              text_select=True, confirm_close=False)
        webview.start()            # blocks; native window is the ONLY UI surface
        started = True
    except Exception as e:
        import traceback as _tb
        try:
            with open(Path(sys.executable).parent / "aether_launch.log", "a") as f:
                f.write(f"[launch] webview failed: {e}\n{_tb.format_exc()}\n")
        except Exception:
            pass
        ctypes.windll.user32.MessageBoxW(
            0,
            f"Aether could not start its native window:\n{e}\n\n"
            "WebView2 may be missing or blocked. Install the WebView2 Runtime "
            "from Microsoft, then relaunch Aether.",
            "Aether", 0x10)
    while True:
        time.sleep(3600)
```

## Verify (on the user's machine)

1. Kill orphans: `taskkill /F /IM Aether.exe`, then launch the installed exe
   via `terminal(background=true)` directly (`C:/Users/valte/AppData/Local/Aether/Aether.exe`).
   - Expect: `tasklist | grep Aether.exe` == 1, `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8732/ui/` == 200, no `aether_launch.log` written.
2. Launch a **second** instance (simulates double-clicking the shortcut again):
   - Expect: it exits cleanly ("already running — focusing it" in the second
     proc's output), total `Aether.exe` processes stays **1**, NO browser opens,
     no `aether_launch.log`. The first window is brought to the foreground.
3. Compare structure to the working `Hermes One.lnk`: target = `…\hermes-agent.exe`,
   no args, WorkDir = exe folder, Icon = exe,0. Aether's `.lnk` follows the same
   pattern, so the lnk is never the cause — only the app's launch logic is.

## Notes

- `MUTEX_NAME` is `Global\` so it works across session/integrity levels on
  single-user desktops; use `Local\` if you ever need per-session isolation.
- The `EnumWindows` callback MUST return `False` (0) after finding the window to
  stop enumeration; returning `True` keeps walking and may match other windows.
- Do NOT keep a `webbrowser.open` browser fallback — it is what produced the
  "opens in default browser" complaint. If WebView2 is genuinely gone, tell the
  user via MessageBox; they reinstall the runtime once.
- `winshell` shortcut objects have no `.save()` method; to (re)point a `.lnk`
  use `win32com.client.Dispatch("WScript.Shell").CreateShortcut(path)` then
  `.Save()`.
