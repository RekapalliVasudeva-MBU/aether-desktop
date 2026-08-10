# Azure Container Apps Deployment (Portal Steps + GitHub Actions)

## When to Use
The laptop-hosted site (project_rag) needs to run 24/7 without the laptop on. Container Apps is the cost-optimized serverless target: scales to zero, pay-per-request, ~$5-15/mo for low traffic.

---

## Portal Setup (No CLI Required)

### 1. Resource Group
- Portal → **Resource groups** → **Create**
- Name: `aethermind-rg`
- Region: `South India` (or closest)
- **Review + Create**

### 2. App Registration (for GitHub Actions OIDC)
- Portal → **Microsoft Entra ID** → **App registrations** → **New registration**
- Name: `github-actions-aethermind`
- Supported account types: **Single tenant**
- Redirect URI: **Web** → `https://github.com`
- **Register**
- **Copy**: Application (client) ID → `AZURE_CLIENT_ID`
- **Copy**: Directory (tenant) ID → `AZURE_TENANT_ID`

### 3. Federated Credential (GitHub → Azure)
- In App Registration → **Certificates & secrets** → **Federated credentials** → **Add credential**
- Scenario: **GitHub Actions deploying Azure resources**
- Organization: `RekapalliVasudeva-MBU`
- Repository: `project_rag`
- Entity type: **Branch**
- Branch name: `main`
- Name: `github-main`
- Description: `GitHub Actions OIDC for project_rag main branch`
- Audience: `api://AzureADTokenExchange`
- **Add**

### 4. Verify Service Principal (Enterprise App)
- Portal → **Enterprise applications** → **All applications**
- Search `github-actions-aethermind` → Click it
- Confirm **Object ID** (e.g., `4661da4d-e9a0-44ff-9ca2-a5c128cbd8aa`)

### 5. Grant Contributor Role on Resource Group
- Portal → **Resource groups** → `aethermind-rg` → **Access control (IAM)**
- **Add** → **Add role assignment**
- Role: **Contributor** (generic, NOT Container Registry variants)
- Assign access to: **User, group, or service principal**
- Select members → Search `github-actions-aethermind` → Select the **Enterprise Application**
- **Review + assign**

### 6. Get Subscription ID
- Portal → **Subscriptions** → Click your subscription → **Overview**
- Copy **Subscription ID** → `AZURE_SUBSCRIPTION_ID`

### 7. (Optional) Log Analytics Workspace
- Portal → **Log Analytics workspaces** → **Create**
- Resource group: `aethermind-rg`
- Name: `aethermind-logs`
- Region: `South India`
- After deploy → **Settings** → **Agents** → Copy **Workspace ID** + **Primary key**

---

## GitHub Secrets (Add to Repo Settings → Secrets → Actions)

| Secret | Value |
|--------|-------|
| `AZURE_CLIENT_ID` | App Registration → Application (client) ID |
| `AZURE_TENANT_ID` | App Registration → Directory (tenant) ID |
| `AZURE_SUBSCRIPTION_ID` | Subscriptions → Subscription ID |
| `OPENROUTER_API_KEY` | Your OpenRouter key |
| `RAG_GITHUB_REPO` | `RekapalliVasudeva-MBU/project_rag` |
| `RAG_GITHUB_PATH` | `pdfs` |
| `RAG_GITHUB_REF` | `main` |
| `RAG_PG_DSN` | (optional) Postgres DSN |
| `AZURE_LOG_ANALYTICS_WORKSPACE_ID` | (optional) Log Analytics Workspace ID |
| `AZURE_LOG_ANALYTICS_WORKSPACE_KEY` | (optional) Log Analytics Primary key |

---

## Dockerfile (Multi-Stage, CPU-Only, GHCR)

```dockerfile
# builder stage - installs deps in venv
FROM python:3.11-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ libpq-dev && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && pip install --no-cache-dir -r requirements.txt

# runtime stage - only runtime deps
FROM python:3.11-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libgomp1 libpq5 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser -s /bin/bash appuser
WORKDIR /app
COPY --chown=appuser:appuser . .
RUN mkdir -p /app/rag_vector_db /app/rag_pdfs /app/dashboard_log && chown -R appuser:appuser /app
USER appuser
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HOST=0.0.0.0 PORT=8000 RAG_PDF_SOURCE=github TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 CHROMA_DB_IMPL=duckdb+parquet ANONYMIZED_TELEMETRY=False CHROMA_DB_DIR=/data/rag_vector_db
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz', timeout=5)" || exit 1
EXPOSE 8000
CMD ["gunicorn", "server:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120", "--keep-alive", "5", "--max-requests", "1000", "--max-requests-jitter", "50", "--preload"]
```

### Pinned Requirements (Compatible Versions)
```
PyMuPDF>=1.24.0,<2
docling==1.20.0
torch>=2.0.0,<3 --index-url https://download.pytorch.org/whl/cpu
transformers>=4.36.0,<5
chromadb==0.6.3
sentence-transformers>=2.2.0,<3
pillow>=10.0.0,<11
fastapi>=0.110.0,<1
uvicorn>=0.29.0,<1
sse-starlette>=2.0.0,<3
python-multipart>=0.0.9,<1
psycopg2-binary>=2.9.0,<3
rank-bm25>=0.2.0,<1
openai>=1.0.0,<2
python-dotenv>=1.0.0,<2
rich>=13.7.0,<14.0.0
tqdm>=4.0.0,<5
gunicorn>=21.0.0,<22
opentelemetry-api>=1.20.0,<2
opentelemetry-sdk>=1.20.0,<2
```

Key compatibility fixes:
- `docling==1.20.0` (pinned, avoids backtracking)
- `torch` CPU-only via `--index-url https://download.pytorch.org/whl/cpu` (no CUDA bloat)
- `chromadb==0.6.3` (pinned, avoids version resolution)
- `rich>=13.7.0,<14.0.0` (docling 1.20.0 depends on `rich<14,>=13.7`)

---

## Server.py Changes Required

### 1. Health Endpoints
```python
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}  # liveness probe, no DB

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "chunks": collection.count(),
        "queue_position": len(_request_queue),
        "current_request": bool(_current),
        "model": CONFIG["openrouter_model"],
        "postgres": store.enabled,
    }  # readiness probe
```

### 2. Graceful Shutdown
```python
import signal
_shutdown = False

def _signal_handler(signum, frame):
    global _shutdown
    _shutdown = True

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        signal.signal(signal.SIGTERM, _signal_handler)
        signal.signal(signal.SIGINT, _signal_handler)
    except Exception:
        pass
    asyncio.create_task(queue_worker())
    store.connect()
    if CONFIG.get("rag_pdf_source", "local") == "github":
        await _ingest_github_assets()
    try:
        yield
    finally:
        print("[shutdown] Graceful shutdown complete")
```

### 3. Configurable ChromaDB Path
```python
CHROMA_DB_DIR = os.environ.get("CHROMA_DB_DIR", str(PROJECT_DIR / "rag_vector_db"))
client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
```

---

## GitHub Actions Workflows

### `.github/workflows/build-push.yml`
- Trigger: push to main (paths: server.py, main.py, web_ui/**, requirements.txt, Dockerfile, .dockerignore)
- Build multi-stage Dockerfile
- Push to GHCR with metadata tags
- Test image: pull → run container → curl /healthz → curl /api/health → test /api/chat (expects OpenRouter error)

### `.github/workflows/deploy-azure.yml`
- Trigger: workflow_run on build-push success, or manual dispatch
- Azure login via OIDC (`azure/login@v2` with federated credentials)
- Create Container Apps Environment if missing
- Create Container App if missing (min-replicas=0, max=3, CPU=1, Memory=2Gi, ingress external, target-port=8000)
- Scale rule: http concurrent requests = 10
- Update image if exists
- Verify deployment: curl /healthz + /api/health on Container App FQDN

---

## Cost Optimization
- **min-replicas=0** → scales to zero when idle ($0)
- **CPU=1, Memory=2Gi** → enough for docling+ChromaDB on CPU
- **max-replicas=3** → caps max concurrent cost
- **Container Apps** → pay per vCPU-second + GiB-second, not per hour
- **No GPU** → docling runs on CPU (slower ingest, cheaper)
- **Ephemeral storage** → ChromaDB re-ingests on cold start (mount Azure Files for persistence if needed)

---

## Frontend Integration (GitHub Pages)
After deploy, workflow outputs `DEPLOYMENT_URL` (e.g., `https://aethermind-rag.xxx.southindia.azurecontainerapps.io`)

Update `web_ui/index.html`:
```javascript
const apiBase = 'https://your-container-app-fqdn';  // or use CNAME api.yourdomain.com
```

CORS: server.py allows all origins (`*`) — update for production if needed.

---

## Verification Checklist
- [ ] Resource group created
- [ ] App Registration + Federated Credential + Enterprise App verified
- [ ] Contributor role assigned on RG to Enterprise App
- [ ] Subscription ID copied
- [ ] GitHub secrets added
- [ ] Docker builds locally (`docker build -t aethermind-rag:test .`)
- [ ] GitHub Actions build-push passes
- [ ] GitHub Actions deploy-azure passes
- [ ] Container App FQDN returns 200 on /healthz and /api/health
- [ ] Frontend calls backend successfully
- [ ] Cold start re-ingests from GitHub (check logs for "Indexed X chunks")