---
name: markdown-to-pdf
description: Convert markdown files to high-quality PDFs using markdowntoword.io.
version: "1.0"
author: Hermes Agent
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [pdf, markdown, conversion]
    category: productivity
---

# Markdown to PDF Skill

Convert `.md` files to professional, readable PDFs using the markdowntoword.io web tool — the only converter that produces acceptable output quality per user testing.

## When to Use

- User asks to convert a markdown file to PDF
- User needs lecture notes, documentation, or analysis docs in PDF format
- Any `.md` → `.pdf` conversion request

## Prerequisites

- Playwright MCP browser available (for automated upload/download)
- Source `.md` file exists on disk

## Procedure

### Step 1: Copy file to Playwright's allowed root

Playwright's `browser_file_upload` only accepts files under its allowed roots. Copy the source file:

```bash
cp "/c/Users/<user>/path/to/file.md" "/c/Users/<user>/AppData/Local/hermes/hermes-agent/.playwright-mcp/file.md"
```

### Step 2: Navigate and upload

1. Navigate to `https://markdowntoword.io/tools/markdown-to-pdf`
2. **Do NOT click the "Choose File" button** — it is a styled `<input type="file">` and the visible SVG icon / sticky page header intercept pointer events, so `browser_click` times out with `TimeoutError: ... intercepts pointer events`.
3. Set the file directly with the unsafe-run tool (most reliable method):
   ```js
   // mcp_playwright_browser_run_code_unsafe
   async (page) => {
     await page.locator('input[type=file]').setInputFiles('/abs/path/.playwright-mcp/file.md');
     return 'file set';
   }
   ```
   *Alternative:* click the drop-zone to open the OS file chooser, then call `mcp_playwright_browser_file_upload`. This only works while the chooser modal is open, so it is flaky — prefer `setInputFiles`.
4. Verify the file name / line count now appears in the editor textbox and the Live Preview pane renders (headings, tables, code blocks).

### Step 3: Wait for preview and download

1. Wait ~8 seconds for the live preview to render
2. Verify the "Download as PDF" button is enabled (not disabled)
3. Click "Download as PDF"
4. Wait for the download to complete (check events for filename)

### Step 4: Move to target location

The download lands in `.playwright-mcp/` with a name derived from the markdown title (e.g. `Hermes-Agent-Architecture.pdf`), NOT a fixed `output.pdf`. Locate and copy it:

```bash
ls -t "/c/Users/<user>/AppData/Local/hermes/hermes-agent/.playwright-mcp/"*.pdf | head -1
cp "<that file>" "/c/Users/<user>/target/path/desired-name.pdf"
```

## Pitfalls

- **NEVER use md2pdf, mdpdf, fpdf2, or WeasyPrint** — they produce garbage output on Windows. WeasyPrint requires GTK/Pango which isn't available. mdpdf produces unreadable PDFs with bad fonts and no formatting. User explicitly rejected these.
- **File must be under Playwright's allowed root** — direct paths like `C:\Users\valte\Documents\file.md` will be rejected with "File access denied". Always copy to `.playwright-mcp/` first.
- **5MB file size limit** on markdowntoword.io — for very large files, split them or use alternative approaches.
- **Wait for preview** — the Download button is disabled until the preview renders. Don't click too early.
- **Clicking "Choose File" fails** — the upload `<input type=file>` is visually hidden behind an SVG/header; Playwright `browser_click` times out with "intercepts pointer events". Use `browser_run_code_unsafe` + `setInputFiles` (Step 2) instead of `browser_click` or `browser_file_upload`.
- **`browser_file_upload` needs a live modal** — it errors with "can only be used when there is related modal state present" unless the OS chooser is currently open. Don't rely on it; use `setInputFiles`.

## Verification

After conversion, check the output PDF exists and has reasonable size (>10KB for content, not 0 bytes):

```bash
ls -la "/c/Users/<user>/target/path/output.pdf"
```
