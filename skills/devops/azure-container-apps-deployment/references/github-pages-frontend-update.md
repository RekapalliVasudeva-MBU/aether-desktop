# GitHub Pages Frontend Update for Azure Backend

## Pattern: Inject Azure Backend FQDN via Query Parameter

The GitHub Pages frontend (`gh-pages` branch `index.html`) uses a configurable API base URL pattern:

```javascript
const DEFAULT_API_BASE = 'https://aethermind-rag.eastasia.azurecontainerapps.io';
const apiBase = (window.__AETHER_API_BASE__ || new URLSearchParams(window.location.search).get('api') || DEFAULT_API_BASE).replace(/\/$/, '');
function apiUrl(path) { const p = path.startsWith('/') ? path : `/${path}`; return apiBase ? `${apiBase}${p}` : p; }
```

**How it works:**
1. `DEFAULT_API_BASE` - Your Azure Container App FQDN (e.g., `https://aethermind-rag.eastasia.azurecontainerapps.io`)
2. Override via `?api=https://your-backend.com` query parameter for testing
3. Override via `window.__AETHER_API_BASE__` set before script loads

## Update Procedure

When Container App FQDN changes, update the gh-pages branch:

```bash
# Get current sha of gh-pages index.html
gh api /repos/<owner>/<repo>/contents/index.html?ref=gh-pages --jq '.sha'

# Create updated HTML with new FQDN
# (Use the same index.html template but update DEFAULT_API_BASE)

# Push to gh-pages branch
gh api /repos/<owner>/<repo>/contents/index.html -X PUT \
  -F message="Update gh-pages index.html for new Azure Container App FQDN" \
  -F branch=gh-pages \
  -F content=<base64-encoded-html> \
  -F sha=<current-sha>
```

## Template: gh-pages index.html

See `templates/gh-pages-index.html` for the complete template with:
- `DEFAULT_API_BASE` set to your Azure Container App FQDN
- Query param override support (`?api=`)
- Global variable override (`window.__AETHER_API_BASE__`)
- All API calls using `apiUrl(path)` helper

## CORS Configuration

Ensure your Container App CORS allows the GitHub Pages origin:

```bash
# In Container App config, add CORS allowed origins:
# https://aethermind.page
# https://your-custom-domain.com
# https://<github-username>.github.io
```

Or in `server.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://aethermind.page", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Testing

```bash
# Test with query param override
https://aethermind.page/?api=https://your-backend.azurecontainerapps.io

# Verify API calls go to correct backend
# Open browser dev tools → Network tab → check API call URLs
```