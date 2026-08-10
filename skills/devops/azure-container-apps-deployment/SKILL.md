---
name: azure-container-apps-deployment
description: Deploy containerized Python apps (FastAPI, RAG, agent backends) to Azure Container Apps with cost optimization for free/student subscriptions.
version: "1.0"
author: "Hermes Agent"
license: "MIT"
platforms: ["linux", "windows", "macos"]
tags: ["azure", "container-apps", "deployment", "devops", "cost-optimization"]
category: "devops"
---

# Azure Container Apps Deployment Skill

Deploy containerized Python apps (FastAPI, RAG, agent backends) to Azure Container Apps with cost optimization for free/student subscriptions.

## When to Use

- Deploying a containerized Python backend (FastAPI, RAG API, agent server) to Azure
- Target is Azure Container Apps (serverless containers, scale-to-zero)
- Subscription has region/policy restrictions (e.g., Azure for Students)
- Need cost optimization: scale-to-zero, no persistent Log Analytics, minimal resources

## Prerequisites

- Azure subscription with Contributor access on a resource group
- Docker image pushed to a public registry (GHCR, Docker Hub) or private ACR
- Azure CLI installed and authenticated (`az login`)
- Resource group created

## Procedure

### 1. Prepare the Docker Image

```dockerfile
# Multi-stage build for minimal size
FROM python:3.11-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ libpq-dev && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

FROM python:3.11-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libgomp1 libpq5 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser -s /bin/bash appuser
WORKDIR /app
COPY --chown=appuser:appuser . .
RUN mkdir -p /app/rag_vector_db /app/rag_pdfs /app/dashboard_log && chown -R appuser:appuser /app
USER appuser
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HOST=0.0.0.0 PORT=8000 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz', timeout=5)" || exit 1
EXPOSE 8000
CMD ["gunicorn", "server:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120", "--keep-alive", "5", "--max-requests", "1000", "--max-requests-jitter", "50", "--preload"]
```

Key optimizations:
- Use `--extra-index-url https://download.pytorch.org/whl/cpu` for CPU-only PyTorch (avoids CUDA bloat)
- Pin docling version (`docling==1.20.0`) to avoid dependency resolution hell
- Use `gunicorn` with `--preload` for memory sharing
- Single worker, uvicorn worker class
- Health check endpoint `/healthz` (no DB calls)

### 2. Build & Push Image

```bash
docker build -t ghcr.io/<owner>/<repo>:latest .
docker push ghcr.io/<owner>/<repo>:latest
```

Or use GitHub Actions (`.github/workflows/build-push.yml`) for automated builds.

### 3. Create Container Apps Environment (CLI)

**Critical for restricted subscriptions (Azure for Students):**

```bash
# Try Central US first (most commonly allowed)
az containerapp env create --name <env-name> --resource-group <rg> --location "Central US" --logs-destination none

# If Log Analytics required, create workspace in allowed region first:
az monitor log-analytics workspace create --resource-group <rg> --workspace-name <ws-name> --location "Central US"
$workspaceId = az monitor log-analytics workspace show -g <rg> -n <ws-name> --query customerId -o tsv
$workspaceKey = az monitor log-analytics workspace get-shared-keys -g <rg> -n <ws-name> --query primarySharedKey -o tsv
az containerapp env create --name <env-name> --resource-group <rg> --location "Central US" --logs-workspace-id $workspaceId --logs-workspace-key $workspaceKey
```

**Key flags:**
- `--logs-destination none` — skip Log Analytics entirely (saves cost, avoids region restrictions)
- `--logs-workspace-id/key` — use pre-created workspace in allowed region

### 4. Create Container App (CLI)

```bash
az containerapp create \
  --name <app-name> \
  --resource-group <rg> \
  --environment <env-name> \
  --image ghcr.io/<owner>/<repo>:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 3 \
  --cpu 1.0 \
  --memory 2Gi \
  --secrets openrouter-api-key="<key>" \
  --env-vars \
    OPENROUTER_API_KEY=secretref:openrouter-api-key \
    RAG_PDF_SOURCE=github \
    RAG_GITHUB_REPO=<owner>/<repo> \
    RAG_GITHUB_PATH=pdfs \
    RAG_GITHUB_REF=main \
    CHROMA_DB_DIR=/data/rag_vector_db \
    HOST=0.0.0.0 \
    PORT=8000
```

**Cost optimization settings:**
- `--min-replicas 0` — scale to zero when idle (no charge)
- `--max-replicas 3` — limit max cost
- `--cpu 1.0 --memory 2Gi` — minimal viable for docling + ChromaDB
- Single container, no sidecars

### 5. Portal Alternative

If CLI fails due to policy, use Azure Portal:
1. **Container Apps Environments** → Create → Region: Central US → Log Analytics: None
2. **Container Apps** → Create → Select environment → Image: `ghcr.io/...` → Ingress: HTTP, port 8000 → CPU: 1, Memory: 2Gi → Min replicas: 0, Max: 3
3. **Configuration** → Secrets → Add `openrouter-api-key`
4. **Configuration** → Environment variables → Add all env vars, reference secret with `secretref:openrouter-api-key`

### 6. Post-Deploy

- Get FQDN: `https://<app-name>.<region>.azurecontainerapps.io`
- Test: `curl https://<fqdn>/healthz` and `curl -X POST https://<fqdn>/api/chat -H "Content-Type: application/json" -d '{"question":"test"}'`
- Update frontend (GitHub Pages) to call the new backend URL

## Pitfalls & Workarounds

| Issue | Cause | Fix |
|-------|-------|-----|
| `RequestDisallowedByAzure` on env create | Subscription policy blocks region for Log Analytics | Use `--logs-destination none` OR create Log Analytics workspace in allowed region (Central US, East US, West US 2) first |
| `Microsoft.OperationalInsights` locations empty | Provider registration not propagated or Students subscription restriction | Skip Log Analytics (`--logs-destination none`) or use pre-created workspace |
| Docker build times out | docling pulls massive CUDA deps | Use CPU-only PyTorch index: `--extra-index-url https://download.pytorch.org/whl/cpu` + pin `docling==1.20.0` |
| Image pull fails from GHCR | Image not public or wrong name | Ensure GHCR package visibility is public, or use `docker login ghcr.io` with PAT |
| Container crashes on startup | Missing `/healthz` endpoint or port mismatch | Add `/healthz` returning `{"status":"ok"}`, ensure app binds `0.0.0.0:8000` |
| OOM kills | 2Gi insufficient for docling + ChromaDB | Increase to `--memory 4Gi` or use remote embeddings (OpenRouter) to avoid local models |
| Docling import errors (`PdfFormatOption`, `InputFormat`) | Docling 1.20+ API breaking change - removed `PdfFormatOption`, moved `InputFormat` | Update imports: remove `PdfFormatOption`, change `InputFormat.PDF: PdfFormatOption(pipeline_options=...)` → `InputFormat.PDF: pipeline_options`; import `InputFormat` from `docling.datamodel.base_models` |
| CrossEncoder reranker unavailable | Hugging Face model download blocked in container (no internet) | Falls back to vector similarity; for production, pre-cache model in Docker image or use remote reranker |
| PostgreSQL unavailable | No local Postgres in Container Apps (expected) | Graceful degradation - visitor logging disabled; use external Postgres if needed |
| ChromaDB collection missing on cold start | Fresh container, no persistent volume | Auto-seed from `prebuilt_chunks.json` on startup; add Azure File share for persistence if needed |

## GitHub Actions Integration

Two workflows:
1. `.github/workflows/build-push.yml` — Build → test → push to GHCR on push to main
2. `.github/workflows/deploy-azure.yml` — Deploy to Container Apps (requires OIDC federated credential)

**OIDC Setup:**
```bash
az ad app create --display-name "github-actions-<name>" --web-redirect-uris "https://github.com"
az ad sp create --id <APP_ID>
az role assignment create --assignee <APP_ID> --role Contributor --scope /subscriptions/<SUB>/resourceGroups/<RG>
az ad app federated-credential create --id <APP_ID> --parameters '{"name":"github-main","issuer":"https://token.actions.githubusercontent.com","subject":"repo:<owner>/<repo>:ref:refs/heads/main","audiences":["api://AzureADTokenExchange"]}'
```

**GitHub Secrets needed:**
- `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`
- `OPENROUTER_API_KEY`, `RAG_GITHUB_REPO`, `RAG_GITHUB_PATH`, `RAG_GITHUB_REF`

## References

- `references/healthz-endpoint.md` — Minimal health check implementation
- `references/dockerfile-cpu-only.md` — Optimized Dockerfile template
- `references/region-policy-workaround.md` — Log Analytics region restriction details
- `references/docling-import-fix.md` — Docling 1.20.0+ API change fix (PdfFormatOption removed, InputFormat moved)
- `references/github-pages-frontend-update.md` — GitHub Pages frontend API base configuration for custom domain
- `references/container-app-command-format.md` — Azure CLI command/args format guide
- `references/custom-domain-setup.md` — Custom domain (CNAME + TXT) configuration

## Verification

```bash
# Health check
curl https://<fqdn>/healthz
# Should return: {"status":"ok"}

# Chat test
curl -X POST https://<fqdn>/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"what is RAG"}'
# Should stream tokens back
```