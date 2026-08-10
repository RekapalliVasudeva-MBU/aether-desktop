# FastAPI UploadFile Parameter Fix (Windows Frozen Apps)

## The Bug

FastAPI v2+ with Pydantic v2 requires explicit `File(...)` dependency for `UploadFile` parameters. Missing it causes:

- `POST /api/pdfs/add` → `{"detail":[{"type":"missing","loc":["query","req"],"msg":"Field required"}]}`
- `GET /openapi.json` → "Internal Server Error" (Pydantic rebuild fails)
- `TypeError: TypeAdapter[...] is not fully defined; you should define ... and all referenced types, then call .rebuild()`

## Wrong Code (Causes Error)

```python
from fastapi import UploadFile

@app.post("/api/pdfs/add")
async def api_pdfs_add(file: UploadFile):
    ...
```

## Correct Code

```python
from fastapi import UploadFile, File

@app.post("/api/pdfs/add")
async def api_pdfs_add(file: UploadFile = File(...)):
    ...
```

## Why This Matters for Frozen Apps

In development (`python -m uvicorn`), FastAPI/Pydantic may auto-resolve. In frozen PyInstaller bundles, the type resolution is stricter — **explicit `File(...)` is mandatory**.

## Symptoms in Frozen App

1. User uploads PDF via UI → nothing happens
2. Check logs: "Field required" error
3. API docs at `/docs` or `/openapi.json` fail to load
4. Pydantic error about incomplete TypeAdapter

## Quick Fix Pattern

**Search for:** `file: UploadFile` without `= File(...)`
**Replace with:** `file: UploadFile = File(...)`
**Add import:** `from fastapi import File`

This applies to ALL `UploadFile` parameters in FastAPI endpoints.