---
name: hermes-workflow-engine
description: "Hermes Workflow Engine — n8n-like workflow automation as an MCP server. Create, manage, and execute workflows from Hermes chat."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [workflow, automation, MCP, n8n-alternative]
---

# Hermes Workflow Engine (n8n-like MCP Server)

**Status:** Built and installed as MCP server `workflow_engine` in Hermes config.
**Server path:** `C:\Users\valte\AppData\Local\hermes\hermes-agent\optional-mcps\workflow-engine\server.py`
**Workflow storage:** `C:\Users\valte\AppData\Local\hermes\workflows\`
**MCP tools prefix:** `mcp_workflow_engine_*` (13 tools)

## Quick Start

Server is already added to Hermes config. Start a new session and use directly:
- "List all workflows"
- "Create a workflow that checks disk space"
- "Execute the GPU monitor workflow"
- "Activate the daily briefing workflow"

## Quick Start

1. Install: `pip install mcp` (already present in Hermes venv)
2. Configure in `~/.hermes/config.yaml` under `mcp_servers.workflow_engine`
3. Restart Hermes → tools appear as `mcp_workflow_engine_*`

## Tools

- `health` — check engine status
- `list_workflows` — list all workflows
- `get_workflow` — get workflow by ID
- `create_workflow` — create a new workflow
- `update_workflow` — update existing workflow
- `delete_workflow` — delete a workflow
- `activate_workflow` / `deactivate_workflow` — toggle workflow status
- `execute_workflow` — manually trigger a workflow
- `list_executions` — view execution history
- `get_execution` — get execution details
- `export_workflow` — export workflow as JSON
- `import_workflow` — import workflow from JSON

## Workflow JSON Format

```json
{
  "id": "workflow-1",
  "name": "Daily ML Monitor",
  "active": true,
  "nodes": [
    {
      "id": "trigger-1",
      "type": "manual-trigger",
      "name": "Manual Trigger",
      "position": [0, 0]
    },
    {
      "id": "action-1",
      "type": "shell-command",
      "name": "Check GPU",
      "position": [200, 0],
      "params": {
        "command": "nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu --format=csv,noheader"
      }
    },
    {
      "id": "action-2",
      "type": "webhook",
      "name": "Send Alert",
      "position": [400, 0],
      "params": {
        "url": "https://hooks.example.com/alert",
        "method": "POST",
        "body": "GPU Status: {{$node.action-1.output}}"
      }
    }
  ],
  "connections": {
    "trigger-1": { "main": [{ "node": "action-1", "type": "main", "index": 0 }] },
    "action-1": { "main": [{ "node": "action-2", "type": "main", "index": 0 }] }
  }
}
```

## Supported Node Types

| Type | Description |
|------|-------------|
| `manual-trigger` | Manually triggered from chat |
| `shell-command` | Execute a shell command |
| `webhook` | HTTP request to external URL |
| `delay` | Wait N seconds |
| `condition` | IF/ELSE branching |
| `telegram-message` | Send Telegram message |
| `email` | Send email via SMTP |
| `python-code` | Execute Python code snippet |
| `sub-workflow` | Call another workflow |
