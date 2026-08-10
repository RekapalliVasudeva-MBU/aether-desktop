# Docling Import Fix (docling 1.20.0+ API Change)

## Problem

In docling 1.20.0+, the `PdfFormatOption` class was removed/moved from `docling.document_converter`. The old import pattern:

```python
from docling.document_converter import DocumentConverter, PdfFormatOption
```

fails with:
```
ImportError: cannot import name 'PdfFormatOption' from 'docling.document_converter'
```

## Root Cause

Docling API changed. The `DocumentConverter` now accepts `pipeline_options` directly in the `format_options` dict, without wrapping in `PdfFormatOption`.

## Fix

**Old (broken):**
```python
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions

pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = True
# ...

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)
```

**New (working):**
```python
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions

pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = True
# ...

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: pipeline_options  # Pass directly, no wrapper
    }
)
```

## Key Changes

| Old | New |
|-----|-----|
| `from docling.document_converter import DocumentConverter, PdfFormatOption` | `from docling.document_converter import DocumentConverter` |
| `InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)` | `InputFormat.PDF: pipeline_options` |

## When This Happens

- Upgrading docling to 1.20.0+ (or any version where API changed)
- Building Docker images that pull latest docling from PyPI
- CI/CD pipelines that don't pin docling version

## Prevention

Pin docling version in requirements.txt:
```
docling==1.20.0
```

And test imports locally before deploying:
```bash
python -c "from docling.document_converter import DocumentConverter; print('OK')"
```