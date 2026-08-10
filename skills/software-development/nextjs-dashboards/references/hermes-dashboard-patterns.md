# Hermes Dashboard Integration Patterns

API routes and CLI commands for connecting a Next.js dashboard to Hermes Agent on Windows.

## Hermes CLI Commands

| Command | Purpose |
|---------|---------|
| `hermes --version` | Get version string (parse with `/v?(\d+\.\d+\.\d+)/`) |
| `hermes gateway status` | Check if gateway is running — look for "running" or "✓" |
| `hermes gateway start` | Start the gateway |
| `hermes gateway stop` | Stop the gateway |
| `hermes config show` | Full config dump |
| `hermes mcp` | Interactive MCP catalog picker (terminal only) |

## Config File Locations

| File | Path |
|------|------|
| Config | `%LOCALAPPDATA%\hermes\config.yaml` |
| Secrets | `%LOCALAPPDATA%\hermes\.env` (blocked by read_file) |
| Workflows | `%USERPROFILE%\.hermes\workflows\` |

## MCP Server Config

Read from `config.yaml` → `mcp_servers:` section. Each server has `command`, `args`, `enabled`, `timeout`.

Server status detection:
- Gateway running + `enabled: true` → `connected`
- `enabled: false` → `disconnected`
- `firecrawl` is typically disabled (needs API key)

## API Server (Optional)

Hermes dashboard chat requires the API server:
- Port: `8642`
- Enable: Set `API_SERVER_ENABLE=true` in `.env`
- Key: Set `API_SERVER_KEY=<any-secret>` in `.env`
- Restart: `hermes gateway restart`

Without this, the Live Chat tab shows instructions to enable it.

## Reading Config from Next.js

```typescript
// Use powershell since read_file blocks some system files
const config = execSync(
  'powershell -Command "Get-Content $env:LOCALAPPDATA\\hermes\\config.yaml"',
  { timeout: 5000, encoding: 'utf8' }
);
const modelMatch = config.match(/default:\s*(.+)/);
```
