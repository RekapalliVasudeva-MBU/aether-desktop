---
name: rag-system-development
title: RAG System Development
version: 1.2.0
author: Hermes Agent
description: Complete workflow for converting Jupyter notebooks into production-ready Retrieval-Augmented Generation (RAG) systems with GPU acceleration and professional package structure.
created: 2025-06-23
last_modified: 2026-07-11
status: active
---

# RAG System Development Skill

**Purpose**: Complete workflow for converting Jupyter notebooks into production-ready Retrieval-Augmented Generation (RAG) systems with GPU acceleration and professional package structure.

**User Preference**: Focus on practical results, concise responses, and direct instructions. Stop verbose explanations, show working results, and make it functional the first time.

**FAITHFUL REPLICATION RULE**: When converting/replicating a user's EXISTING
notebook or project, mirror their exact component stack (docling, specific model
names, chunking approach, etc.). Do NOT swap in libraries you prefer "for
stability" — the user rejected a PyMuPDF-for-docling substitution and reverted to
their docling pipeline. If you think a component is wrong, ASK; don't silently replace.

## HARD RULE: Verify, Do NOT Assert Success

The user caught repeated fabricated "✅ success" reports where the code was never actually run. This is the #1 failure mode for this class of task.

- After writing/editing code, you MUST actually execute it (run the pipeline, or at minimum a real import/syntax check) and paste the REAL output.
- Never describe a run as "successful" / "working" / "fixed" unless you have terminal output proving it.
- If you cannot run it (no GPU env, blocked, wrong interpreter), say so explicitly and give the exact command for the user to run — do NOT invent output.
- Use a self-terminating test harness (see templates/run_test.py): import the pipeline, run it headless, print the result, exit. Prefer this over interactive `main.py` when verifying, so the run completes and notifies.
- When the user says "run it and fix the errors" / "u run it ok now", that is an explicit instruction to execute, not to narrate.


## When to Use

Use this skill when you need to:
- Convert Jupyter notebooks containing RAG logic into production Python applications
- Set up professional package structure with proper dependencies and testing
- Build GPU-accelerated document processing pipelines using PyMuPDF and ChromaDB
- Create interactive chat interfaces for RAG systems
- Package models for distribution via pip install

## Core Components

**Practical Approach**: Skip explanations, show working solutions. If it doesn't work, fix it until it does, don't stop at a non-working solution.

**Code Style**: Direct, minimal, and functional. No marketing prose, no unnecessary explanations.

### 1. Package Structure
```
RAG-System-Production/
├── main.py                    # Core RAG application  (ONE executable — prefer this)
├── setup.py                   # Package configuration (optional)
├── README.txt                # Documentation
├── requirements.txt           # Dependency list
└── rag_pdfs/                  # Source docs + temp_split_chunks/ subfolder
    └── temp_split_chunks/     # Cached per-N-page PDF splits
```

> **Single-file first.** For notebook→Python conversions, ship ONE executable `main.py`. Only create a `src/` package when the user explicitly asks for package layout. A mirrored `src/` copy drifts from `main.py` and keeps stale/broken imports while the real file works — see Pitfall 6.

### 2. Key Dependencies
```python
install_requires=[
    "PyMuPDF>=1.24.0",           # PDF processing (fitz). NOT "fitz" on PyPI
    "torch>=2.0.0",              # ML framework (CUDA build for GPU)
    "transformers>=4.36.0",     # Tokenizers/ML models
    "chromadb>=0.4.0",           # Vector database
    "sentence-transformers>=2.2.0",  # Embedding generation
    "ollama>=0.4.0",             # Local LLM client (if using Ollama)
    "pillow>=10.0.0",            # Image processing
]
```

> **PDF extraction — MATCH what the user's source already uses. DO NOT substitute.**
> If the user's notebook/project uses **docling** (`DocumentConverter` +
> `HybridChunker`), you MUST keep docling in the converted app — do NOT silently
> swap it for PyMuPDF. The user explicitly rejected a PyMuPDF substitution and
> reverted to the docling pipeline from their `First_Rag.ipynb`. Conversely, if
> their source uses PyMuPDF, keep PyMuPDF. The rule is *faithful replication of
> the user's pipeline*, not "use the lighter library." Verified docling pipeline
> (imports + converter + HybridChunker with `headings` metadata) is in
> `references/docling_api.md`. docling's API does drift across versions (Pitfall 6),
> so verify the exact imports in the installed version before writing them.
> Only prefer PyMuPDF over docling when starting a NEW project from scratch and the
> user hasn't specified a tool.

> **GPU note:** `torch.cuda.is_available()` is per-interpreter. The user's RTX 5070
> CUDA torch lives in conda `ai_env`; VS Code must select that interpreter or the
> code silently falls back to CPU. The code should auto-detect, not hardcode CUDA.

## Workflow Steps

### Step 1: Analyze Source Material
1. **Examine Jupyter notebook structure** - Identify core functions, imports, and logic flow
2. **Extract dependencies** - Note required packages and external APIs
3. **Map data flow** - Trace input → processing → output pipelines
4. **Identify hardware needs** - Determine GPU requirements, memory constraints

### Step 2: Package Setup
1. **Create setup.py** - Professional package configuration with proper metadata
2. **Generate README.txt** - Comprehensive documentation
3. **Set up src structure** - Modular source organization
4. **Configure testing** - pytest setup and verification scripts

### Step 3: Application Development
1. **Replace Jupyter dependencies** - Switch to production-grade libraries
2. **Implement error handling** - Robust exception management and fallbacks
3. **Add documentation** - Inline docstrings and usage examples
4. **Create test coverage** - Unit tests and integration tests

### Step 4: Testing & Verification
1. **Run quick validation** - Import tests to verify syntax
2. **Execute pipeline tests** - Full RAG pipeline functionality
3. **Test interactive features** - Chat interface and query handling
4. **Performance testing** - GPU acceleration and resource usage

## Hybrid Provider Pattern (OpenRouter API + local Ollama)

Make generation switchable between a cloud API and a local model WITHOUT
duplicating the retrieval pipeline. This is the pattern used to convert a
local-only RAG (`project_rag`) into a hybrid copy (`project_rag_hybrid`).

**When to use**: user wants a RAG that answers via OpenRouter (cloud) OR Ollama
(local), picked at runtime/config, not hardcoded to one backend. Also applies
when the user says "make it work with an API instead of the local model" or
"copy the project and make a hybrid version".

**Keep retrieval local; only swap generation.** PyMuPDF →
`all-MiniLM-L6-v2` (local embeddings) → ChromaDB stay unchanged. Only the
final LLM call in `ask_rag_system` is routed by a `provider` field.

**OpenRouter is OpenAI-compatible** — drive it through the `openai` SDK with a
custom base_url; streaming is identical to OpenAI's. Add `openai>=1.0.0` to
`install_requires`:
```python
from openai import OpenAI
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.get("openrouter_api_key") or os.environ.get("OPENROUTER_API_KEY", ""),
    default_headers={"HTTP-Referer": "https://localhost/rag-hybrid", "X-Title": "Hybrid RAG"},
)
stream = client.chat.completions.create(model=MODEL, messages=[...], stream=True)
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```
Default free model: `mistralai/mistral-7b-instruct:free`. (Respect the
`hermes-free-model-policy` HARD rule: only `:free` models for this user.)

**Settings file (`rag_settings.json`)** — persist provider + credentials;
first-run interactive menu writes it, every later run reads it and does NOT
re-prompt; switch by editing the file (or `python main.py --setup`):
```json
{ "configured": true, "provider": "openrouter",
  "openrouter_api_key": "", "openrouter_model": "mistralai/mistral-7b-instruct:free",
  "ollama_model": "richardyoung/qwythos-9b-abliterated:Q4_K_M" }
```
Make `source_folder` project-relative (`PROJECT_DIR / "rag_pdfs"`) so the
copied project is portable and never reads the original's PDFs.

**Robustness details that worked in practice**:
- Lazy-import `ollama` (set `ollama = None` on `ImportError`) so the OpenRouter
  path still runs even if Ollama isn't installed.
- Fall back to the `OPENROUTER_API_KEY` env var when the key field is empty.
- Plain `json.load`/`json.dump` merged onto `DEFAULT_SETTINGS` (no pydantic).
- `if ollama is None: print error; return` inside the local branch.
- Read settings inside `ask_rag_system` with a fallback to `DEFAULT_SETTINGS`
  so ad-hoc test scripts (e.g. `query_test.py`) that call it without a
  settings arg still work.

**Verify the API branch WITHOUT a key/network**: patch `OpenAI` to return a
fake client yielding fake stream chunks, then assert the request shape
(`model`, `stream=True`, message roles). Also verify the first-run→config→
reuse flow by piping stdin and asserting `rag_settings.json` is written and a
second `configure_settings()` returns the stored provider without prompting.
See `scripts/verify_hybrid.py` (copy into the RAG project and run with
`python verify_hybrid.py`).

> **Security note:** the API key is stored in PLAINTEXT in `rag_settings.json`.
> Tell the user to keep the folder private, or use the env-var fallback instead.

## Common Pitfalls & Solutions

### Pitfall 6: "App opens 2 seconds then closes" — WebView2 Runtime missing on user PCs

### Pitfall 7: Local Docker build times out on massive dependency resolution for docling + PyTorch

**Symptom:** `docker build` runs for 5+ minutes, pulls 500MB+ of CUDA packages, then times out or fails with dependency backtracking (pip spends forever resolving `opencv-python-headless`, `matplotlib`, `nvidia-*` transitive deps from docling).

**Root cause:** docling 1.20.0 has a massive transitive dependency tree (easyocr → scikit-image → opencv, matplotlib, numpy, plus PyTorch CUDA wheels). Building from `python:3.11-slim` in a container without layer caching or pre-built wheels hits this wall every time.

**Fix (used in this session):**

1. **Use the CPU-only PyTorch index in requirements.txt:**
   ```txt
   torch>=2.0.0,<3
   # then in Dockerfile:
   RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt
   ```

2. **Prefer GitHub Actions build over local Docker:** The hosted runner has layer caching and no 5-min timeout. Push to main → Actions builds → pushes to GHCR in ~6 min. Local `docker build` with no cache is the anti-pattern here.

3. **If local build required:** Use a pre-built PyTorch base image (`pytorch/pytorch:2.1-cpu`) if available, or split the Dockerfile so torch installs first with `--no-deps`, then the rest. The approach that finally worked: CPU index URL + Actions runner.

**Verification:** Build log shows `torch-2.13.0+cpu` (191 MB) pulled from the CPU index, NOT the full CUDA stack (526 MB + 366 MB + 170 MB nvidia packages). Total image size ~2.5 GB vs >4 GB with CUDA.

This is the #1 cause of "installed .exe fails to launch" for pywebview-based apps (Aether, Hermes desktop, etc.) on fresh Windows machines. The dev machine has Edge/WebView2; clean user machines often don't. `webview.create_window()` throws → process dies silently with no window and no error box.

**Detection (registry check):**
```python
import winreg
try:
    winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                   r"SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications")
    # present
except Exception:
    # MISSING -> this is the bug
```

**Permanent fix (two layers):**

1. **App-level pre-flight** in `desktop_app.py` (before `create_window()`):
   ```python
   def _webview2_installed() -> bool:
       try:
           winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                          r"SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications")
           return True
       except Exception:
           pass
       # side-by-side WebView2Loader.dll also accepted
       for p in (Path(sys.executable).parent / "WebView2Loader.dll",
                 Path(sys.executable).parent / "_internal" / "WebView2Loader.dll"):
           if p.exists(): return True
       return False

   def _install_webview2() -> bool:
       # download Evergreen bootstrapper, run /silent /install, show progress box
       # return True on success
   ```

   If missing → auto-install or show a message box with the manual install URL. **Do NOT call `create_window()` until the runtime is present.**

2. **Installer-level bundling** (`make_installer.py` + `installer_boot.py`):
   Download the 1.7 MB Evergreen bootstrapper (`https://go.microsoft.com/fwlink/p/?LinkId=2124703`) at build time, bundle it into the payload, and run it `/silent /install` during setup BEFORE launching the app. This makes fresh users never hit the missing-runtime crash. Payload size increases by ~1.7 MB.

Full implementation pattern in `skills/windows-app-launch-debug/references/webview2_missing_runtime.md`.


on docling 2.110.0. The class names also renamed (`AcceleratorOptions` not `AcceleratorOptions`... actually
`AcceleratorOptions` exists; the removed one was the `format_options` submodule). Meanwhile a duplicated
`src/` package (with its own broken `document_processor.py`) sat next to a working `main.py` that never imported it —
the user kept "running document_processor.py" and hitting the dead code.

**Solution**:
- Verify the EXACT API in the installed version before writing imports:
  `python -c "import docling; print(docling.__version__); from docling.datamodel.base_models import InputFormat; from docling.document_converter import PdfFormatOption"`
  In docling >=2.x: `InputFormat` is in `docling.datamodel.base_models`; `PdfFormatOption` in
  `docling.document_converter`; accelerator classes (`AcceleratorDevice`, `AcceleratorOptions`) in
  `docling.datamodel.pipeline_options`. There is NO `docling.format_options` module.
- Prefer NOT generating a mirrored `src/` package. If you do, delete it the moment `main.py` works rather than
  maintaining two copies. If the user runs a `src/` file that fails to import, check whether that file is even
  on the execution path for the real app — often it isn't.
- See references/docling_api.md for the verified import map.

## Code Patterns

### Professional Error Handling
```python
try:
    import pycuda.autopilot as cuda
    # GPU-accelerated processing
except ImportError:
    # CPU fallback
    print("⚠️ CUDA not available, using CPU fallback")
    device = "CPU"
```

### Dependency Management
```python
# Check for optional dependencies
def check_dependencies():
    required = ["PyMuPDF", "torch", "chromadb"]
    optional = ["cuda", "tensorflow", "spark"]
    
    for dep in required:
        try:
            __import__(dep.lower().replace("-", "_").replace(".", "_"))
            print(f"✓ {dep} available")
        except ImportError:
            print(f"❌ {dep} required but not found")
            return False
    
    return True
```

### Performance Optimization
```python
class EfficientTextProcessor:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = None
        self.max_tokens = 512
    
    def process_in_chunks(self, text, chunk_size=100):
        """Process text in manageable chunks to protect VRAM"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            chunks.append(" ".join(chunk))
        
        return chunks
```

## Verification Commands

### Installation Test
```bash
pip install -e .
```

### Quick Import + Syntax Test (real, fast)
```bash
python -c "import ast,sys; ast.parse(open('main.py').read()); print('syntax OK')"
python -c "import sys; sys.path.insert(0,'.'); import main; print('IMPORT OK')"
```

### Pipeline Test (HEADLESS — preferred for verification)
```bash
python run_test.py      # builds DB over ALL pdfs, asks a sample question, exits
```
Use a self-terminating harness so the run completes and you can paste real output.
For a long CPU embed over many PDFs, run in background with notify_on_complete.

### Interactive Test
```bash
python main.py
```

### Sanity check the index size
After a run, `collection.count()` should reflect ALL pdfs (e.g. ~380 for 35 pdfs),
not a single file's worth (~12). If it's small, re-check Pitfall 5.

## Best Practices

1. **Hardware Detection**: Always check for GPU availability with graceful fallbacks
2. **Memory Management**: Process data in chunks to prevent VRAM overflow
3. **Error Recovery**: Implement comprehensive error handling and retry logic
4. **Testing First**: Write tests before implementing features
5. **Documentation**: Maintain comprehensive inline and external documentation
6. **Performance Monitoring**: Track resource usage and optimize bottlenecks

## Troubleshooting

### Common Errors & Solutions

1. **Import Errors**
   - Use `try/except` blocks for optional dependencies
   - Implement fallback mechanisms for missing packages
   - Cache downloaded models locally

2. **Memory Issues**
   - Process data incrementally
   - Use smaller batch sizes
   - Monitor GPU usage during execution

3. **Performance Problems**
   - Profile code to identify bottlenecks
   - Optimize text processing algorithms
   - Use efficient data structures

4. **Setup Issues**
   - Validate environment before running pipeline
   - Check for required permissions and dependencies
   - Use virtual environments for isolation

## Quick Reference

| Command | Purpose |
|---------|---------|
| `pip install -e .` | Install package |
| `python test_rag.py` | Run quick tests |
| `python main.py` | Start interactive RAG |
| `pytest` | Run full test suite |

## Resources

### Tools
- **PyMuPDF**: High-performance PDF processing (`fitz`)
- **ChromaDB**: Vector database for semantic search
- **Ollama**: Local LLM integration
- **Sentence Transformers**: Pre-trained embedding models

### Support files in this skill
- `references/docling_api.md` — verified docling import map + the full `DocumentConverter`/`HybridChunker` RAG pipeline this user's `First_Rag.ipynb` uses (with `headings` metadata + CUDA/CPU perf notes). READ THIS before writing/replicating a docling pipeline.
- `references/sync_hybrid_search_bugs_2026-07-25.md` — critical bugs in `sync_hybrid_search_with_citations` (ChromaDB `get()` ordering, missing metadata `id`, relevance filter using wrong defaults), plus duplicate functions in aether config, uptime endpoint bug, Cloudflare tunnel hardcoded path, and RRF score normalization. Run the reproduction script in this file to verify bugs before fixing.
- `templates/run_test.py` — self-terminating verification harness (see Verification Commands)
- `scripts/verify_hybrid.py` — verify the hybrid OpenRouter+Ollama provider pattern (mocked API branch + first-run→config→reuse flow) without a key or network

### Documentation
- **README.txt**: Complete system documentation
- **Setup Guide**: Package installation and configuration
- **API Reference**: Function documentation and examples

### Testing
- **Quick Tests**: Basic functionality verification
- **Integration Tests**: Complete pipeline testing
- **Performance Tests**: Resource usage and timing

This skill provides a complete framework for transforming Jupyter RAG notebooks into production-ready applications with proper packaging, testing, and documentation standards.