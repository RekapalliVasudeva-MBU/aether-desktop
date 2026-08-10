---
name: markdown-to-pdf-conversion
description: Convert markdown files to PDF using markdowntoword.io via browser automation.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms:
- windows
- linux
- macos
metadata.hermes:
  tags: markdown, pdf, conversion, browser
  category: productivity
  related_skills: []
  config: {}
---

# Markdown to PDF Conversion Skill

## When to Use
Use this skill when you need to quickly convert a markdown (.md) file to a PDF without installing local software, especially for sharing documentation, reports, or notes that require a fixed layout.

## Prerequisites
- Access to a web browser (Chromium-based) via Hermes' built-in browser tools.
- The markdown file you wish to convert must be accessible (local path or via Hermes file system).
- Internet connection to reach https://markdowntoword.io/tools/markdown-to-pdf.

## How to Run
1. Ensure the markdown file exists in Hermes file system (use `write_file` or `read_file` to verify).
2. Navigate to the conversion site with `browser_navigate`.
3. Upload the markdown file using the file input element.
4. Trigger the conversion (click the "Download as PDF" button).
5. Retrieve the resulting PDF (it will be downloaded; you can then move or open it as needed).

## Quick Reference
- **Tool**: `browser_navigate`, `browser_cdp` / `browser_snapshot` / `browser_type` / `mcp_chrome_devtools_*` for file upload and button clicks.
- **URL**: https://markdowntoword.io/tools/markdown-to-pdf
- **File input selector**: `input[type="file"]`
- **Download button selector**: button containing text "Download as PDF"

## Procedure
1. **Prepare markdown**  
   ```text
   write_file(path="C:/Users/valte/OneDrive/prime_practice/rag_pdfs/doc.md", content="# Sample\nThis is a test.")
   ```
2. **Open converter**  
   ```text
   browser_navigate(url="https://markdowntoword.io/tools/markdown-to-pdf")
   ```
3. **Upload file**  
   - Use CDP to set file input (or use `mcp_chrome_devtools_upload_file` if available).  
   - Example via CDP:  
     ```text
     mcp_chrome_devtools_upload_file(uid="<file-input-uid>", filePath="C:/Users/valte/OneDrive/prime_practice/rag_pdfs/doc.md")
     ```
   - If the uid is unknown, first snapshot the page:  
     ```text
     browser_snapshot()
     ```
     then find the input element with type="file" and get its uid from the snapshot.
4. **Trigger download**  
   - Locate the button with inner text "Download as PDF" and click it via `mcp_chrome_devtools_click` or `browser_click` after obtaining its ref.  
   - Example:  
     ```text
     browser_snapshot()
     ```
     find button ref
     `browser_click(ref="@<button-ref>")`
5. **Wait for download**  
   - Optionally poll for the downloaded file in the default download folder or use Hermes' process monitoring if you saved the file to a known location.
6. **Verify PDF**  
   - Use `read_file` (if saved locally) or move the file to desired location and check its size >0.

## Pitfalls
- The site may block automated uploads if it detects bot-like behaviour; keep interactions (rare). Add a small delay or human-like interaction if needed.
- File input uid changes on each page reload; always obtain the uid from a fresh snapshot before uploading.
- The download button may be disabled until a file is successfully uploaded; ensure upload completes before clicking.
- The site returns the PDF as a download; Hermes does not automatically capture downloads unless you specify a known download directory (e.g., set `browser.download.dir` via CDP or configure the browser profile). For simplicity, after clicking download, you can retrieve the PDF from the default downloads folder (`%USERPROFILE%\Downloads`) and move it.

## Verification
- After download, confirm the PDF exists and is not empty:  
  ```text
  read_file(path="C:/Users/valte/Downloads/doc.md.pdf", limit=1)   # or appropriate extension
  ```
- Optionally validate PDF header (`%PDF-`) using `read_file` and checking first few bytes.

## References
- See `references/markdowntoword-info.md` for additional information about the conversion service.

## Templates
- None.

## Scripts
- None.