# Aether WebView2 Stale Cache Fix (2026-07-30)

## Problem
After rebuilding Aether.exe with UI/JS fixes, the WebView2 window still showed a stale non-functional UI — buttons didn't work, chat input was non-functional, despite the backend being healthy.

## Root Cause
WebView2 aggressively caches HTML served by the local FastAPI backend. After rebuilding the EXE with fixes to `index.html` or `build_entry.py`, WebView2 continued serving the OLD cached HTML from a previous broken build.

## Fix Applied
Added cache-busting query parameter to WebView2 URL in two places:

1. `build_entry.py` `launch_webview()`:
```python
import time as _time
cb = int(_time.time())
url = f"http://127.0.0.1:{port}/?cb={cb}"
window = webview.create_window("Aether — Agent + RAG", url, ...)
webview.start(debug=True)
```

2. `desktop_app_fixed.py` `_launch_webview()`:
```python
cache_buster = int(time.time())
url = f"http://127.0.0.1:{port}/?cb={cache_buster}"
window = webview.create_window("Aether — Agent + RAG", url, ...)
webview.start(debug=True, storage_path=storage_path)
```

## Key Insight
`build_entry.py` (the frozen EXE entry point) has its OWN `launch_webview()` function separate from `desktop_app_fixed.py`. Both must be patched — fixing only one is insufficient.