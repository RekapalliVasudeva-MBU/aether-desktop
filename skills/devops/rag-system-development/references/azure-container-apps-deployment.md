# Azure Container Apps Deployment for RAG Systems

## Overview
Deploy a RAG backend (FastAPI + ChromaDB + docling pipeline) to Azure Container Apps with GitHub Actions CI/CD. This avoids VM management, scales to zero (cost savings), and integrates with GitHub OIDC for keyless auth.

## Architecture
- **Frontend**: GitHub Pages (custom domain) → static HTML/JS
- **Backend**: Azure Container Apps (serverless containers)
- **Vector DB**: ChromaDB on ephemeral storage (re-ingests on cold start) or Azure Files volume for persistence
- **Auth**: GitHub Actions OIDC → Azure App Registration (no client secrets)
- **Secrets**: GitHub Actions secrets (OpenRouter key, GitHub repo config)

## Prerequisites
- Azure subscription (Azure for Students works)
- GitHub repo with Dockerfile, requirements.txt, server.py, main.py
- Azure CLI + GitHub CLI (`gh`) installed locally

## Step 1: Create Azure Resources (one-time)

### Resource Group
```bash
az group create --name aethermind-rg --location eastus
```

### App Registration (for GitHub OIDC)
```bash
# Create App Registration
az ad app create --display-name "github-actions-aethermind" --web-redirect-uris "https://github.com"
# Note the APP_ID (client-id) from output

# Create Service Principal
az ad sp create --id <APP_ID>

# Federated Credential (links GitHub Actions to Azure)
az ad app federated-credential create --id <APP_ID> --parameters '{
  "name": "github-main",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:OWNER/REPO:ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"]
}'

# Grant Contributor on Resource Group
az role assignment create --assignee <APP_ID> --role Contributor --scope /subscriptions/<SUB_ID>/resourceGroups/aethermind-rg

# Get Tenant ID + Subscription ID
az account show --query "{tenantId: tenantId, id: id}" -o tsv
```

### (Optional) Log Analytics Workspace
```bash
az monitor log-analytics workspace create --resource-group aethermind-rg --workspace-name aethermind-logs --location eastus
az monitor log-analytics workspace get-shared-keys --resource-group aethermind-rg --workspace-name aethermind-logs
```

## Step 2: GitHub Repository Secrets
Add these in GitHub → Settings → Secrets and variables → Actions:

| Secret | Value |
|--------|-------|
| `AZURE_CLIENT_ID` | App Registration Application (client) ID |
| `AZURE_TENANT_ID` | Directory (tenant) ID |
| `AZURE_SUBSCRIPTION_ID` | Subscription ID |
| `OPENROUTER_API_KEY` | `sk-or-...` |
| `RAG_GITHUB_REPO` | `owner/repo` (where PDFs live) |
| `RAG_GITHUB_PATH` | `pdfs` |
| `RAG_GITHUB_REF` | `main` |
| `RAG_PG_DSN` | (optional) Postgres DSN for visitor logs |
| `AZURE_LOG_ANALYTICS_WORKSPACE_ID` | (optional) |
| `AZURE_LOG_ANALYTICS_WORKSPACE_KEY` | (optional) |

## Step 3: GitHub Actions Workflows

### `.github/workflows/build-push.yml`
```yaml
name: Build and Push Docker Image
on:
  push:
    branches: [main]
    paths: ['server.py', 'main.py', 'web_ui/**', 'requirements.txt', 'Dockerfile', '.dockerignore']
jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=ref,event=branch
            type=sha,prefix=
            type=raw,value=latest,enable={{is_default_branch}}
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### `.github/workflows/deploy-azure.yml`
```yaml
name: Deploy to Azure Container Apps
on:
  workflow_run:
    workflows: ["Build and Push Docker Image"]
    types: [completed]
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - name: Deploy Container App
        run: |
          az containerapp up \
            --name aethermind-rag \
            --resource-group aethermind-rg \
            --environment aethermind-env \
            --image ghcr.io/${{ github.repository }}:latest \
            --target-port 8000 \
            --ingress external \
            --min-replicas 0 \
            --max-replicas 3 \
            --cpu 1.0 \
            --memory 2Gi \
            --secrets \
              openrouter-api-key=${{ secrets.OPENROUTER_API_KEY }} \
              rag-github-repo=${{ secrets.RAG_GITHUB_REPO }} \
              rag-github-path=${{ secrets.RAG_GITHUB_PATH }} \
              rag-github-ref=${{ secrets.RAG_GITHUB_REF }} \
            --env-vars \
              OPENROUTER_API_KEY=secretref:openrouter-api-key \
              OPENROUTER_MODEL=openrouter/free \
              RAG_PDF_SOURCE=github \
              RAG_GITHUB_REPO=secretref:rag-github-repo \
              RAG_GITHUB_PATH=secretref:rag-github-path \
              RAG_GITHUB_REF=secretref:rag-github-ref \
              CHROMA_DB_DIR=/data/rag_vector_db \
              HOST=0.0.0.0 \
              PORT=8000 \
            --registry-server ghcr.io \
            --registry-identity system
```

## Step 4: Frontend Integration
Update GitHub Pages `index.html` to call the Container App URL:
```javascript
const apiBase = 'https://aethermind-rag.xxx.eastus.azurecontainerapps.io';
// or custom domain: api.yourdomain.com
```

## Cost Optimization
- `min-replicas: 0` → scales to zero when idle ($0/hour)
- CPU 1.0, Memory 2Gi → ~$5-15/month for low traffic
- No GPU → CPU-only docling (slower ingestion, cheaper)
- ChromaDB on ephemeral storage → free, re-ingests on cold start

## Verification
After deploy, the workflow outputs the Container App FQDN. Test:
```bash
curl https://<FQDN>/healthz
curl -X POST https://<FQDN>/api/chat -H "Content-Type: application/json" -d '{"question": "what is RAG"}'
```

## Common Issues
| Issue | Fix |
|-------|-----|
| Azure Login fails | Verify federated credential subject matches `repo:OWNER/REPO:ref:refs/heads/main` |
| Container App won't start | Check logs: `az containerapp logs show --name aethermind-rag --resource-group aethermind-rg` |
| Image pull fails | Ensure GHCR image is public or use `--registry-identity system` with managed identity |
| OOM kills | Increase `--memory` to 4Gi or use remote embeddings (OpenRouter) |

## References
- [Azure Container Apps docs](https://learn.microsoft.com/azure/container-apps/)
- [GitHub OIDC with Azure](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-azure)
- [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/)