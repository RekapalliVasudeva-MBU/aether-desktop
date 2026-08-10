# Custom Domain Setup for Azure Container Apps

## DNS Records Required

For a custom domain like `api.aethermind.page` pointing to your Container App:

| Type | Name | Value |
|------|------|-------|
| **CNAME** | `api` | `<container-app-fqdn>` (e.g., `aethermind-rag.yellowhill-09aa2600.eastasia.azurecontainerapps.io`) |
| **TXT** | `asuid.api` | `<custom-domain-verification-id>` (from Azure Portal) |

## Azure Portal Steps

1. Go to **Container App** → **Custom domains**
2. Click **Add** → Enter `api.aethermind.page`
3. Azure shows required CNAME and TXT records
4. Add both records at your domain registrar
5. Wait for DNS propagation (5-30 minutes)
6. Click **Validate** → **Add binding**

## Automated DNS Validation

```bash
# Check if CNAME resolves
nslookup api.aethermind.page

# Check TXT record
nslookup -type=TXT asuid.api.aethermind.page
```

## Important Notes

- **CNAME target** must be the exact Container App FQDN (not a wildcard)
- **TXT record** uses `asuid.{subdomain}` format (e.g., `asuid.api`)
- **Verification ID** is shown in Azure Portal Custom domains page
- **HTTPS** is automatic once bound (Azure manages TLS certificate)
- **Multiple subdomains** can point to same Container App (different bindings)

## GitHub Pages Integration

After custom domain binds:
1. Update gh-pages `DEFAULT_API_BASE` to `https://api.aethermind.page`
2. Test: `curl https://api.aethermind.page/healthz`
3. Frontend at `https://aethermind.page/` now calls `https://api.aethermind.page/api/chat`