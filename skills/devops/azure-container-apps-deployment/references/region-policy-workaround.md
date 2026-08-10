# Log Analytics Region Restriction Workaround

## Problem

Azure for Students (and some other restricted subscriptions) have policies that block Log Analytics workspace creation in certain regions. The error:

```
(RequestDisallowedByAzure) Resource '<workspace-name>' was disallowed by Azure: This policy maintains a set of best available regions where your subscription can deploy resources.
```

When creating a Container Apps Environment, Azure tries to auto-create a Log Analytics workspace in the same region. If that region is blocked for `Microsoft.OperationalInsights`, the entire env creation fails.

## Root Cause

- `Microsoft.App` (Container Apps) may be allowed in a region
- `Microsoft.OperationalInsights` (Log Analytics) may be blocked in the same region
- Students subscriptions often have hidden region restrictions not visible in provider registration

## Workarounds

### Option 1: Skip Log Analytics Entirely (Recommended for Cost)

```bash
az containerapp env create --name <env-name> --resource-group <rg> --location "Central US" --logs-destination none
```

**Pros:** Zero Log Analytics cost, no region restrictions, simpler
**Cons:** No built-in logging/analytics (use stdout/stderr + external logging)

### Option 2: Pre-create Workspace in Allowed Region

```bash
# 1. Create workspace in allowed region (Central US, East US, West US 2 typically work)
az monitor log-analytics workspace create --resource-group <rg> --workspace-name <ws-name> --location "Central US"

# 2. Get credentials
$workspaceId = az monitor log-analytics workspace show -g <rg> -n <ws-name> --query customerId -o tsv
$workspaceKey = az monitor log-analytics workspace get-shared-keys -g <rg> -n <ws-name> --query primarySharedKey -o tsv

# 3. Create env pointing to workspace (can be in different region!)
az containerapp env create --name <env-name> --resource-group <rg> --location "Central US" --logs-workspace-id $workspaceId --logs-workspace-key $workspaceKey
```

**Pros:** Full logging/analytics
**Cons:** Requires finding an allowed region for Log Analytics

### Option 3: Use Portal with "Show environments in all regions"

In Azure Portal:
1. Create Container Apps Environment
2. Enable **"Show environments in all regions"**
3. Select a region that works (try Central US, East US, West US 2)
4. Log Analytics: **None** or create new in allowed region

## Testing Allowed Regions

```bash
# Check which regions are available for Log Analytics
az provider show -n Microsoft.OperationalInsights --query "resourceTypes[?resourceType=='workspaces'].locations" -o table

# Check Container Apps regions
az provider show -n Microsoft.App --query "resourceTypes[?resourceType=='containerApps'].locations" -o table
```

If locations array is empty, provider registration may not have propagated, or subscription has hidden restrictions.

## Typical Allowed Regions for Students Subscriptions

| Region | Container Apps | Log Analytics |
|--------|----------------|---------------|
| Central US | ✅ Usually | ✅ Usually |
| East US | ✅ Usually | ✅ Usually |
| West US 2 | ✅ Usually | ✅ Usually |
| South India | ✅ Often | ❌ Often blocked |
| East Asia | ❌ Often | ❌ Often |
| UK South | ❌ Often | ❌ Often |

**Strategy:** Try Central US first → East US → West US 2.

## Specific Policy Restriction Pattern (Discovered Aug 2024)

Some Azure for Students subscriptions have a custom policy (`sys.regionrestriction`) that **explicitly allows only 5 regions**:

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

## Cost Implications

| Option | Monthly Cost (idle) | Monthly Cost (active) |
|--------|---------------------|----------------------|
| `--logs-destination none` | $0 (scale to zero) | ~$5-15 (CPU/memory only) |
| Log Analytics workspace | $0 (scale to zero) | ~$5-15 + Log Analytics ingestion (~$2.50/GB) |

**Recommendation:** Use `--logs-destination none` for development/student projects. Use external logging (stdout to file, or ship logs to Loki/Elastic) if needed.

## Verification

After env creation:
```bash
az containerapp env show --name <env-name> --resource-group <rg> --query "properties.logAnalyticsConfiguration" -o json
```

Should show either `null` (none) or workspace configuration.