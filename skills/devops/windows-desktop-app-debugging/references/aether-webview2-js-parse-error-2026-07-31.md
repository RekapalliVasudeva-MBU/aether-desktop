# WebView2 JS Parse Error — Backtick in Template Literal (2026-07-31)

## Problem
Aether.exe WebView2 window showed two console errors on every load:
1. `Uncaught SyntaxError: Unexpected end of input` at `index.html:873`
2. `Uncaught ReferenceError: applyAppearance is not defined` at `index.html:873:9`

## Root Cause
`desktop_ui/index.html` line 846 had an **embedded backtick** inside a `${...}` template literal expression:
```
${up.release_notes?<details><summary>Release notes</summary><pre ...
```
The backtick (`` ` ``) immediately after `?` prematurely closed the outer template literal string, causing a JS parse error that broke the **entire** `<script>` block (lines 230–872). Since `applyAppearance()` was defined in that same block (line 700), it was never registered, causing the ReferenceError at line 873.

## Fix
Changed line 846 to use a safe ternary with no embedded backtick:
```
${up.release_notes ? `<details><summary>Release notes</summary><pre style="white-space:pre-wrap;color:var(--muted);font-size:12px">${esc(up.release_notes)}</pre></details>` : ''}
```
Key: space between `release_notes` and `?`, then `` ` `` starts the template literal at the TOP level of the expression, not nested inside `${...}`.

## Secondary Fixes in Same Session
- Added `?cb=<timestamp>` cache-busting to WebView2 URL in `build_entry.py` (line 77-78) to prevent stale HTML after rebuilds
- Changed `debug=False` → `debug=True` in `build_entry.py` so JS errors surface in WebView2 console
- Added `for` attribute to 10 `<label>` elements that were missing them (accessibility fix)

## Verification
1. Rebuild exe: `python build_exe.py`
2. Kill old Aether.exe first (it holds port 8732 and locks `_internal/*.pyd`)
3. Launch new exe
4. Check WebView2 console — no JS errors
5. Verify `/ui/logo.png` returns 200
6. Test RAG chat: `curl -X POST http://127.0.0.1:8732/api/chat -d '{"message":"hello","mode":"rag"}'` — should receive SSE stream

## Related
- Same root-cause pattern as the WebView2 stale UI issue (2026-07-30) — backtick in template literal broke JS parsing
- See `windows-desktop-app-packaging` skill for the full WebView2 stale UI four-layer breakdown