# Azure Container Apps: Container Startup Command Format

## Problem

When setting the container startup command via Azure CLI for Container Apps, the `--command` and `--args` parameters have specific format requirements. Incorrect formats cause the command to be stored as a single string instead of an array, leading to startup failures.

## Correct Format

### Using `--command` and `--args` (Recommended)

```bash
az containerapp update \
  --name <app-name> \
  --resource-group <rg> \
  --command gunicorn \
  --args "server:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120 --keep-alive 5 --max-requests 1000 --max-requests-jitter 50 --preload"
```

This produces the correct JSON structure:
```json
{
  "command": ["gunicorn"],
  "args": ["server:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120", "--keep-alive", "5", "--max-requests", "1000", "--max-requests-jitter", "50", "--preload"]
}
```

### Using `--set` (For Complex Cases)

```bash
az containerapp update \
  --name <app-name> \
  --resource-group <rg> \
  --set properties.template.containers[0].command='["gunicorn","server:app","--workers","1","--worker-class","uvicorn.workers.UvicornWorker","--bind","0.0.0.0:8000","--timeout","120","--keep-alive","5","--max-requests","1000","--max-requests-jitter","50","--preload"]'
```

## Common Mistakes

| Mistake | Result | Fix |
|---------|--------|-----|
| Single string with spaces: `--command "gunicorn server:app ..."` | Command stored as `["gunicorn server:app ..."]` - fails | Use `--command gunicorn --args "..."` |
| Missing quotes on `--args` | Shell splits args incorrectly | Always quote the args string |
| Using `--set` with `[` `]` | CLI treats as env var name (invalid chars) | Use JSON array format with escaped quotes |

## Verification

Check the deployed command format:
```bash
az containerapp show --name <app-name> --resource-group <rg> --query properties.template.containers[0].command -o json
az containerapp show --name <app-name> --resource-group <rg> --query properties.template.containers[0].args -o json
```

Should return arrays, not single strings.

## Force New Revision

To deploy command changes immediately:
```bash
az containerapp update \
  --name <app-name> \
  --resource-group <rg> \
  --image <image>:latest \
  --revision-suffix v2  # Forces new revision
```