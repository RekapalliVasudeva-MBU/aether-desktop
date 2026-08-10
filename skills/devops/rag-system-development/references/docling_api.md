# docling API — verified import map (docling >= 2.x, tested on 2.110.0)

The `docling.format_options` module does NOT exist in modern docling. Imports that
broke (`ModuleNotFoundError: No module named 'docling.format_options'`) must be
rewritten to the locations below.

## Correct imports (verified working)
```python
import docling
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    AcceleratorOptions,
    AcceleratorDevice,       # enum: AcceleratorDevice.CUDA / .CPU
)
from docling.datamodel.base_models import InputFormat
```

## How to verify the API in the user's installed version BEFORE writing imports
```bash
python - <<'PY'
import docling
print("docling", docling.__version__)
from docling.datamodel.base_models import InputFormat
from docling.document_converter import PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions, AcceleratorDevice
print("all imports OK")
PY
```

## Verified docling RAG pipeline (this user's `First_Rag.ipynb`)
Use this verbatim when replicating a docling-based RAG. It converts PDFs to
markdown and chunks structurally, preserving `headings` (H1/H2) metadata that
goes into ChromaDB.

```python
import fitz  # PyMuPDF — only for pre-splitting huge PDFs (smart on-disk cache)
from pathlib import Path
import torch
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions, AcceleratorOptions, AcceleratorDevice
)
from docling.chunking import HybridChunker
from transformers import AutoTokenizer

# Hardware: CUDA if available, else CPU (auto-detect, never hardcode)
_device = AcceleratorDevice.CUDA if torch.cuda.is_available() else AcceleratorDevice.CPU

def build_converter():
    po = PdfPipelineOptions()
    po.do_ocr = True                  # keep True unless PDFs are text-native; else blank text
    po.generate_page_images = False
    po.accelerator_options = AcceleratorOptions(num_threads=4, device=_device)
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=po)}
    )

def get_pdf_chunks(pdf_path, temp_folder, max_pages=8):
    """Split big PDFs into cached 8-page chunks to protect VRAM."""
    doc = fitz.open(pdf_path)
    total = len(doc)
    if total <= max_pages:
        doc.close(); return [pdf_path]
    chunks = []
    for start in range(0, total, max_pages):
        end = min(start + max_pages - 1, total - 1)
        cp = temp_folder / f"{pdf_path.stem}_part_{start+1}_to_{end+1}.pdf"
        if not cp.exists():                 # SMART CACHE: don't re-split
            cd = fitz.open(); cd.insert_pdf(doc, from_page=start, to_page=end)
            cd.save(cp); cd.close()
        chunks.append(cp)
    doc.close(); return chunks

SUPPORTED = [".pdf", ".docx", ".txt", ".odt", ".pptx"]
conv = build_converter()
tok = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
chunker = HybridChunker(tokenizer=tok, max_tokens=512, merge_peers=True)

final_chunks = []
for pdf in Path("rag_pdfs").iterdir():
    if not pdf.is_file() or pdf.suffix.lower() not in SUPPORTED:
        continue
    units = get_pdf_chunks(pdf, Path("rag_pdfs/temp_split_chunks"), 8) if pdf.suffix.lower()==".pdf" else [pdf]
    for unit in units:
        doc = conv.convert(unit).document
        for c in chunker.chunk(dl_doc=doc):
            final_chunks.append({
                "text": c.text,
                "source": pdf.name,
                "headings": c.meta.headings,   # preserves H1/H2; flatten to " > ".join() for ChromaDB
            })
```

### ChromaDB metadata note
ChromaDB metadata must be flat (str/int/float). Convert the headings list:
```python
headings_str = " > ".join(chunk["headings"]) if chunk["headings"] else "No Header"
metadatas.append({"source": chunk["source"], "headings": headings_str})
```
Use `client.delete_collection(name)` in try/except then `get_or_create_collection`
so a rebuild doesn't leave stale vectors.

### Embedding model must match the chunker tokenizer
`emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")`
— same `all-MiniLM-L6-v2` the HybridChunker's tokenizer uses.

## Performance reality check (observed)
- On CPU, docling OCR is SLOW. A 103-page PDF is ~13 chunks, each ~10–30s. A full
  25-PDF build took ~10 min. Run in background with notify_on_complete and DO NOT
  interrupt it — the code deletes the old ChromaDB collection first, so an
  interrupted run leaves a half-built/empty DB.
- One chunk hit `std::bad_alloc` under CPU OCR memory pressure on a giant PDF;
  docling recovered and continued (chunk count still correct). Not fatal.
- On the user's RTX 5070 (CUDA torch in conda `ai_env`), `AcceleratorDevice.CUDA`
  engages automatically — far faster. Ensure the running interpreter is the one
  with the CUDA torch build.

## When to use docling vs PyMuPDF
- **Replicating a user's existing project**: use whatever THEY used. If their
  notebook uses docling, keep docling — do not substitute PyMuPDF (user rejected this).
- **Brand-new project, no tool specified**: PyMuPDF (`fitz.open(pdf); page.get_text()`)
  is lighter and version-stable for plain-text RAG; reach for docling only when you
  need layout/table/OCR awareness.
