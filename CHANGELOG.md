# Changelog

All notable changes to Aether. Version format: `MAJOR.MINOR.PATCH` (Aether uses a
3-part scheme; see `VERSION` if added). Entries grouped by type.

## [1.3.1]

- **Fix: app opens 2s then closes on fresh user PCs.** Root cause: Microsoft
  WebView2 Runtime missing and `desktop_app.py` assumed it was present (no
  detection/fallback), so `webview.create_window()` threw and the process died
  silently. Added a WebView2 pre-flight check that auto-installs the Evergreen
  Runtime (or shows a clear manual-install message) before launching the window.
- Installer (`Aether-Setup.exe`) now bundles the WebView2 bootstrapper and
  installs the runtime as a prerequisite during setup, so new users never hit
  the missing-runtime crash.

## [1.3.0] — current

- Full Sessions panel redesign + add-file + context meter.

## [1.2.9]

- Sessions: `selectSession` switches to Chat view (was a silent no-op).
- App won't open: robust single-instance mutex (verifies other instance is serving,
  takes over zombie; fixed ctypes errcheck crash).
- RAG: ingested 25 PDFs (344 chunks) into ChromaDB; resilient batch ingest.

## [1.2.8]

- Execution-step animation (thinking/tool_start/tool_end timeline in chat).
- Two-layer context compaction (preserve_last_n + 32KB tool-output Snip cap).
- Fuse PDF + Hermes insights into system prompt.

## [1.2.7]

- Sessions panel (sidebar list + load/delete, JSON storage).
- web_search fix (DuckDuckGo POST returns real results).
- DELETE /api/sessions endpoint.

## [1.2.6]

- Rename Hermes One → Aether branding.
- Settings Appearance/Data backend (appearance + backup export/import).
- Fix frozen-exe uvicorn isatty crash.
