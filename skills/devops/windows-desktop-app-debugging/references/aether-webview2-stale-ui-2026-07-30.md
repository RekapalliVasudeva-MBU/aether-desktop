# WebView2 Stale UI Fix - 2026-07-30

Session: Aether.exe built and backend healthy but WebView2 UI stale/non-functional.

Root cause: WebView2 serves cached HTML from previous broken build. Fix: add cache-busting (?cb=<timestamp>) to URL and debug=True.

Fix pattern in desktop_app_fixed.py _launch_webview():
  import time
  cache_buster = int(time.time())
  url = f"http://127.0.0.1:{port}/?cb={cache_buster}"
  window = webview.create_window("Aether - Agent + RAG", url, ...)
  webview.start(debug=True, storage_path=storage_path)

Verification: after rebuild, launch app, check WebView2 loads fresh HTML with interactive buttons. Check app_stdout.log for JS errors if buttons still dont work.
