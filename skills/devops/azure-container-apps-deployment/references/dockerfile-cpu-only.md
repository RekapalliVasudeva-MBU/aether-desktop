# Optimized Dockerfile for CPU-only PyTorch + docling

```dockerfile
# =============================================================================
# Multi-stage Dockerfile for Python RAG/agent backends
# Optimized for: minimal size, CPU-only PyTorch, fast builds
# =============================================================================

# ---- Stage 1: Build dependencies ----
FROM python:3.11-slim AS builder

# Install only essential system deps for building wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment for clean dependency isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python deps with CPU-only PyTorch index
COPY requirements.txt .
# Install torch CPU-only first (no CUDA deps), then rest
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# ---- Stage 2: Runtime image ----
FROM python:3.11-slim AS runtime

# Install only runtime system deps (no build tools)
# libgl1 + libgomp1 for OpenCV/docling, libpq5 for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libgomp1 \
    libpq5 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy application code (respects .dockerignore)
COPY --chown=appuser:appuser . .

# Create directories for data persistence (will be mounted as volumes in Azure)
RUN mkdir -p /app/rag_vector_db /app/rag_pdfs /app/dashboard_log \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Environment variables for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    RAG_PDF_SOURCE=github \
    # Memory optimization: disable tokenizer parallelism, limit threads
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    # ChromaDB settings for lower memory
    CHROMA_DB_IMPL=duckdb+parquet \
    ANONYMIZED_TELEMETRY=False

# Health check endpoint (lightweight, no DB connection)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz', timeout=5)" || exit 1

# Expose port
EXPOSE 8000

# Use gunicorn for production (single worker, low memory)
# Preload app to share memory across workers (we use 1 worker)
CMD ["gunicorn", "server:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120", "--keep-alive", "5", "--max-requests", "1000", "--max-requests-jitter", "50", "--preload"]
```

## Key Optimizations Explained

| Optimization | Why |
|--------------|-----|
| `--extra-index-url https://download.pytorch.org/whl/cpu` | Installs CPU-only PyTorch (~190MB vs ~500MB+ with CUDA) |
| Pin `docling==1.20.0` | Avoids dependency resolution hell with newer versions |
| `gunicorn --preload` | Shares memory across workers (we use 1 worker) |
| Single uvicorn worker | Minimal memory footprint |
| `--max-requests 1000` | Recycles workers to prevent memory leaks |
| `TOKENIZERS_PARALLELISM=false` | Prevents tokenizer deadlocks in multi-threaded env |
| `OMP_NUM_THREADS=1` | Limits OpenMP threads to 1 |
| Multi-stage build | Strips build tools (gcc, g++) from final image |
| Non-root user | Security best practice |
| `--logs-destination none` compatible | Works with Container Apps `--logs-destination none` |

## Requirements.txt Template

```text
# Core ML / RAG stack
PyMuPDF>=1.24.0,<2
docling==1.20.0
torch>=2.0.0,<3
transformers>=4.36.0,<5
chromadb==0.6.3
sentence-transformers>=2.2.0,<3
pillow>=10.0.0,<11

# Web framework
fastapi>=0.110.0,<1
uvicorn>=0.29.0,<1
sse-starlette>=2.0.0,<3
python-multipart>=0.0.9,<1

# Database
psycopg2-binary>=2.9.0,<3

# Search / ranking
rank-bm25>=0.2.0,<1

# LLM client
openai>=1.0.0,<2

# Config / utils
python-dotenv>=1.0.0,<2
rich>=13.7.0,<14.0.0
tqdm>=4.0.0,<5

# Production WSGI server
gunicorn>=21.0.0,<22

# Observability (optional, lightweight)
opentelemetry-api>=1.20.0,<2
opentelemetry-sdk>=1.20.0,<2
```

## .dockerignore Template

```text
# Git
.git
.gitignore
.gitattributes

# Python cache
__pycache__
*.pyc
*.pyo
*.pyd
.pytest_cache
.coverage
.tox
.mypy_cache
.ruff_cache

# Virtual environments
venv/
.env/
.venv/
env/
pipenv/
poetry/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Data directories (mounted as volumes in production)
rag_vector_db/
rag_pdfs/
dashboard_log/
pdfs/

# Logs
*.log
logs/

# Test / eval outputs
eval_results.json
*.jsonl

# Build artifacts
dist/
build/
*.egg-info/
*.whl

# Documentation
README.md
README.txt
INSTALL.md
*.md

# Deployment configs for other platforms
render.yaml
railway.toml
Procfile

# Local development files
.env
.env.local
.env.example
```