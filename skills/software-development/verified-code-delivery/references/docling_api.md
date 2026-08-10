# docling 2.x — import path changes (reusable probe recipe)

## Symptom
```
ModuleNotFoundError: No module named 'docling.format_options'
```
Happens when code imports from `docling.format_options import InputFormat, PdfFormatOption` on a modern docling (verified on **2.110.0**). That module was removed/relocated.

## Correct imports on docling 2.110.0 (verified installed at C:\Users\valte\AppData\Local\hermes\hermes-agent\venv)
```python
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    AcceleratorOptions,   # NOTE: older code used "AcceleratorOptions"; some docs show "AccelerationOptions" — that name does NOT exist in 2.110
    AcceleratorDevice,
)
from docling.datamodel.base_models import InputFormat
```
Verified present in 2.110.0:
- `docling.datamodel.base_models.InputFormat` ✅
- `docling.document_converter.PdfFormatOption` ✅
- `docling.datamodel.pipeline_options.AcceleratorOptions` ✅ (NOT `AccelerationOptions`)
- `docling.datamodel.pipeline_options.AcceleratorDevice` ✅

## How to probe ANY missing-name error generically
```python
# find the real location of a symbol in an installed package
import importlib, inspect
mod = importlib.import_module("docling.datamodel.pipeline_options")
print([n for n in dir(mod) if "ccel" in n or "evice" in n])
# -> ['AcceleratorDevice', 'AcceleratorOptions']
```
Always import from the CURRENT installed location, not from memory of an old version.

## Note on GPU/CUDA
docling `AcceleratorDevice.CUDA` works only if torch has CUDA. In CPU-only envs the try/except should fall back to `AcceleratorDevice.CPU`. (The Hermes venv used here had torch `2.12.1+cpu`, so CUDA was False.)
