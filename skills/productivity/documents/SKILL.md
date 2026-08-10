---
name: documents
description: "Document creation, editing, and extraction: PDFs, PowerPoint, Markdown to PDF, scanned documents. Use when creating/editing PowerPoint decks, converting Markdown to PDF, extracting text from PDFs/scanned documents, or editing PDF text/typos. Covers: python-pptx for slides, pymupdf/marker-pdf for PDF extraction, markdowntoword.io for MD→PDF, nano-pdf for natural-language PDF editing."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [documents, pdf, pptx, ocr, extraction, slides, powerpoint]
---

# Documents — Creation, Editing, Extraction

## Skill Selection

| Task | Section |
|------|---------|
| Create/edit PowerPoint | §1 PowerPoint |
| Extract text from PDFs | §2 PDF Extraction |
| Convert Markdown to PDF | §2.5 Markdown to PDF |
| Safety-check a zip file | §2.6 Zip Safety |
| Edit PDF text/typos | §3 nano-pdf |

---

## §1 — PowerPoint

### Read Content

```bash
python -m markitdown presentation.pptx
python scripts/thumbnail.py presentation.pptx
```

### Editing Workflow

1. Analyze template with `thumbnail.py`
2. Unpack → manipulate slides → edit content → clean → pack

### Creating from Scratch

Use `pptxgenjs` (npm install -g pptxgenjs) for new decks.

### Design Tips

- Pick a bold, content-informed color palette
- One color should dominate (60-70% visual weight)
- Every slide needs a visual element — image, chart, icon, or shape
- Minimum title size: 36pt; body: 14-16pt
- 0.5" minimum margins
- Avoid: text-only slides, repeated layouts, centered body text, accent lines under titles

### QA

```bash
python -m markitdown output.pptx | grep -iE "xxxx|lorem|ipsum|this.*(page|slide).*layout"
```

Convert to images for visual inspection:
```bash
python scripts/office/soffice.py --headless --convert-to pdf output.pptx
pdftoppm -jpeg -r 150 output.pdf slide
```

---

## §2 — PDF Extraction

### Remote URL Available?

Always try `web_extract` first:
```
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])
```

### Choose Extractor

| Feature | pymupdf (~25MB) | marker-pdf (~3-5GB) |
|---------|-----------------|---------------------|
| Text-based PDF | ✅ | ✅ |
| Scanned PDF (OCR) | ❌ | ✅ |
| Tables | Basic | High accuracy |
| Equations/LaTeX | ❌ | ✅ |
| Markdown output | ✅ (via pymupdf4llm) | ✅ (native) |

**Decision:** Use pymupdf unless you need OCR, equations, or complex layout.

### pymupdf (Lightweight)

```bash
pip install pymupdf pymupdf4llm
python scripts/extract_pymupdf.py document.pdf              # text
python scripts/extract_pymupdf.py document.pdf --markdown    # markdown
python scripts/extract_pymupdf.py document.pdf --tables      # tables
python scripts/extract_pymupdf.py document.pdf --pages 0-4   # specific pages
```

### marker-pdf (High-Quality OCR)

```bash
pip install marker-pdf
python scripts/extract_marker.py document.pdf
marker_single document.pdf --output_dir ./output
```

### Split, Merge, Search

```python
import pymupdf
doc = pymupdf.open("report.pdf")
# Split pages 1-5
new = pymupdf.open()
for i in range(5): new.insert_pdf(doc, from_page=i, to_page=i)
new.save("pages_1-5.pdf")
# Search
for i, page in enumerate(doc):
    if page.search_for("revenue"): print(f"Page {i+1}")
```

---

## §2.5 — Markdown to PDF

### Preferred: Browser-based (markdowntoword.io) — BEST quality

CLI tools (`md2pdf`, `mdpdf`, `fpdf2`) all produce poor-quality PDFs — broken formatting, ugly fonts, missing styling. The user has explicitly rejected their output and will do manual conversion rather than accept low-quality PDFs. **Always use the browser to convert via https://markdowntoword.io/tools/markdown-to-pdf. Only fall back to CLI if the user explicitly approves.**

**Workflow:**
1. Copy the `.md` file into the Playwright allowed root (e.g., `.playwright-mcp/`)
2. Navigate to `https://markdowntoword.io/tools/markdown-to-pdf`
3. Click the upload/drag-drop area to trigger file chooser
4. Upload the `.md` file via `browser_file_upload`
5. Wait for preview to render
6. Click "Download as PDF"
7. Copy the downloaded PDF to the target location

```bash
# Step 1: Copy file to Playwright-allowed path
cp "C:\Users\valte\RAG-lecture\input.md" ".playwright-mcp/input.md"
```

Then in browser:
```
navigate → markdowntoword.io/tools/markdown-to-pdf
click upload area → file chooser opens
file_upload → [".playwright-mcp/input.md"]
wait 3s for preview
click "Download as PDF"
wait 5s for download
```

**Pitfall — Playwright file_upload path restriction:** The Playwright MCP server only allows file uploads from its allowed roots (typically `.playwright-mcp/` in the project directory). Files outside these roots get "File access denied" errors. **Always copy the .md file into the `.playwright-mcp/` directory first** before uploading.

```bash
# Step 7: Move downloaded PDF to target
cp ".playwright-mcp/input.pdf" "C:\Users\valte\RAG-lecture\input.pdf"
```

**Pitfall — Large markdown files:** markdowntoword.io has a 5MB upload limit. For very large .md files (>5MB), split into smaller sections before converting. The website handles multi-page PDFs fine — the limit is the input file size, not the output page count.

**Why not CLI?** All Python MD→PDF libraries have critical flaws on Windows:
- `md2pdf` → requires WeasyPrint → needs GTK/Pango (`libgobject-2.0-0.dll`) → **OSError on Windows**
- `mdpdf` → works but produces ugly output (broken TOC, poor fonts, no proper heading hierarchy)
- `fpdf2` → manual HTML-to-plaintext stripping, no real formatting, looks like plain text

### Fallback: mdpdf (acceptable for quick/draft PDFs only)

If browser is unavailable, `mdpdf` at least runs on Windows:

```bash
pip install mdpdf
mdpdf -o output.pdf input.md
```

**Known quirk:** `mdpdf` may warn `ValueError: bad hierarchy level in row` for markdown files that skip heading levels (e.g., H3 directly under H1). The PDF is still generated — this is a TOC-building issue, not a blocking error. Output quality is significantly worse than browser-based conversion.

### Other platforms (macOS/Linux)

`md2pdf` works if GTK is installed. Install GTK first:
- macOS: `brew install pango gdk-pixbuf`
- Linux: `sudo apt install libpango1.0-dev libgdk-pixbuf2.0-dev` (Debian/Ubuntu)

Then: `pip install md2pdf && md2pdf input.md`

Even on these platforms, browser-based conversion via markdowntoword.io produces better output.

## §2.6 — Safety-checking a zip before extraction

When a user asks you to check a zip for threats, scan without extracting first:

```python
import zipfile

DANGEROUS_EXTS = (".exe", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".msi",
                  ".dll", ".scr", ".com", ".wsf", ".hta", ".cpl", ".inf", ".reg")

with zipfile.ZipFile(path, "r") as z:
    for info in z.infolist():
        fn = info.filename
        # Path traversal: files that escape the zip root
        if fn.startswith("..") or (len(fn) > 1 and fn[1] == ":"):
            print(f"THREAT [PATH TRAVERSAL]: {fn}")
        # Zip bomb: extremely high compression ratio
        if info.file_size > 0 and info.compress_size / info.file_size < 0.03:
            print(f"THREAT [ZIP BOMB SUSPECT]: {fn}")
        # Executables
        if fn.lower().endswith(DANGEROUS_EXTS):
            print(f"EXECUTABLE: {fn} ({info.file_size} bytes)")
```

**Script:** Use [`scripts/zip_safety_check.py`](scripts/zip_safety_check.py) for a ready-to-run zip safety scanner. Usage: `python scripts/zip_safety_check.py <zip_path>`

**Note on `.js` files:** Small `.js` files (50-100 bytes) in source code archives are typically Node.js re-export stubs, not malicious. Check file size before flagging — genuine malware payloads are larger.

**Common false positive:** Antivirus heuristics flag files from WhatsApp/messaging with "leaked" or "crack" in the filename. This is a keyword-based trigger, not a content analysis. If the zip contains only source code (`.ts`, `.py`, `.md`, etc.) with no executables, it's safe.

---

## §3 — nano-pdf

Edit PDFs using natural-language instructions.

```bash
pip install nano-pdf
nano-pdf edit deck.pdf 1 "Change the title to 'Q3 Results'"
nano-pdf edit report.pdf 3 "Update the date from January to February 2026"
```

- Page numbers may be 0-based or 1-based — retry with ±1 if wrong
- Uses an LLM under the hood — requires API key
- Works for text changes; complex layout modifications need different approach
