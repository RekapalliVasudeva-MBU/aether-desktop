# Changelog

All notable changes to Aether. Version format: `MAJOR.MINOR.PATCH` (Aether uses a
3-part scheme; see `VERSION` if added). Entries grouped by type.

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
