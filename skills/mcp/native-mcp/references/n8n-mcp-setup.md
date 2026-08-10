# n8n MCP Bridge Setup

## What It Does

The n8n MCP bridge (by CyberSamuraiX, approved by Nous) connects Hermes to a running n8n instance via stdio. It exposes tools to manage and inspect n8n workflows from Hermes chat.

## Tools (read-safe by default)

- `health` — check n8n connectivity
- `list_workflows` — list all workflows
- `get_workflow` — get workflow details
- `find_workflows` — search workflows
- `list_executions` — view execution history
- `get_execution` — inspect specific execution
- `recent_failures` — find recent failures
- `export_workflow` — export workflow JSON

## Opt-in mutating tools

- `activate_workflow` / `deactivate_workflow`

## Install Steps

1. Install n8n locally:
   ```bash
   npm install -g n8n
   # or Docker: docker run -p 5678:5678 n8nio/n8n
   ```

2. Start n8n:
   ```bash
   n8n start  # runs on http://127.0.0.1:5678
   ```

3. Generate API key in n8n: Settings → API → Create API Key

4. Clone and install the bridge:
   ```bash
   git clone https://github.com/CyberSamuraiX/hermes-n8n-mcp.git
   cd hermes-n8n-mcp
   python -m venv .venv
   # Windows:
   .venv/Scripts/pip install -r requirements.txt
   # Linux/Mac:
   .venv/bin/pip install -r requirements.txt
   ```

5. Add to Hermes:
   ```bash
   echo "y" | hermes mcp --accept-hooks add n8n --command "python" --args "C:/path/to/hermes-n8n-mcp/server.py" --env "N8N_BASE_URL=http://127.0.0.1:5678" --env "N8N_API_KEY=your-key-here"
   ```

## Env Vars

| Variable | Default | Description |
|----------|---------|-------------|
| `N8N_BASE_URL` | `http://127.0.0.1:5678` | n8n instance URL |
| `N8N_API_KEY` | (required) | API key from n8n Settings → API |

## Status (May 2026)

The npm package for n8n is ~800MB+ and installation via `npm install -g n8n` timed out in testing. The custom workflow engine MCP (at `optional-mcps/workflow-engine/`) is recommended as a lightweight local alternative for Windows users.
