---
name: azure-container-deployment
category: devops
description: Troubleshooting Azure container deployments (Container Apps, Container Instances, App Service) with focus on region restrictions, policy blocks, and subscription limitations.
---

# Azure Container Deployment Troubleshooting

## When to Use
- Deploying containerized apps to Azure (Container Apps, ACI, App Service for Containers)
- Encountering "RequestDisallowedByAzure" or region restriction errors
- Working with Azure for Students / free tier subscriptions with region limits
- Log Analytics workspace creation failures
- Policy assignment blocks on container resources

## Prerequisites
- Azure CLI installed and authenticated (`az login`)
- Azure subscription with container deployment permissions
- Container image in a registry (GHCR, Docker Hub, ACR)

## Procedure

### 1. Pre-Deployment Checks (Run First)
```bash
# Check subscription capabilities
az account show --query "{name:name, id:id, state:state}" -o table

# Check Container Apps availability
az provider show -n Microsoft.App --query "resourceTypes[?resourceType=='containerApps'].locations" -o table

# Check Container Instances availability
az provider show -n Microsoft.ContainerInstance --query "resourceTypes[?resourceType=='containerGroups'].locations" -o table

# Check policy assignments blocking deployment
az policy assignment list --resource-group <rg-name> -o table

# Check quota
az vm list-usage --location <region> -o table
```

## Region Selection Strategy
- **Try these regions first** (most commonly allowed for Students/free tiers):
  - Central US
  - East US
  - West US 2
  - East US 2
- **Avoid**: South India, Southeast Asia, Brazil South (often restricted)

## Specific Policy Restriction Pattern (Discovered Aug 2024)

Some Azure for Students subscriptions have a custom policy (`sys.regionrestriction`) that **explicitly allows only 5 specific regions**:

| Allowed Region | Container Apps | Log Analytics (if allowed) |
|----------------|----------------|----------------------------|
| `eastasia` (East Asia) | ✅ | Check per subscription |
| `koreacentral` (Korea Central) | ✅ | Check per subscription |
| `uaenorth` (UAE North) | ✅ | Check per subscription |
| `malaysiawest` (Malaysia West) | ✅ | Check per subscription |
| `austriaeast` (Austria East) | ✅ | Check per subscription |

**Check your specific allowed regions:**
```bash
az policy assignment show --name sys.regionrestriction --query "parameters.listOfAllowedLocations.value" -o tsv
```

If you see a custom `sys.regionrestriction` policy, **you MUST deploy to one of the explicitly allowed regions**. Standard regions like Central US, East US, West US 2 will be blocked even if they appear in provider registration.

### 3. Container Apps Specific
```bash
# Create environment WITHOUT Log Analytics (bypasses common blocker)
az containerapp env create \
  --name <env-name> \
  --resource-group <rg> \
  --location <allowed-region> \
  --logs-destination none
```

### 4. Container Instances (ACI) Alternative
- Simpler, no environment needed
- Different region availability than Container Apps
- Use `--restart-policy OnFailure` and `--ip-address Public`

### 5. App Service for Containers
- Different service, different region availability
- Use "Web App for Containers" tier

## Pitfalls

| Issue | Symptom | Fix |
|-------|---------|-----|
| Region blocked | `RequestDisallowedByAzure` | Try Central US / East US / West US 2 |
| Log Analytics blocked | Workspace creation fails | Use `--logs-destination none` for Container Apps env |
| Policy assignment | Template deployment fails | Check `az policy assignment list --resource-group <rg>` |
| Subscription quota | Quota exceeded errors | Check `az vm list-usage --location <region>` |
| GHCR pull rate limit warning | Warning in ACI portal | Ignore — only applies to Docker Hub |

## Verification
```bash
# Test deployed endpoint
curl https://<fqdn>/healthz
curl -X POST https://<fqdn>/api/chat -H "Content-Type: application/json" -d '{"question": "test"}'
```

## References
- [Azure Container Apps regions](https://learn.microsoft.com/en-us/azure/container-apps/quotas-limits)
- [Azure policy troubleshooting](https://learn.microsoft.com/en-us/azure/governance/policy/troubleshoot)
- [Azure for Students limitations](https://azure.microsoft.com/free/students/)