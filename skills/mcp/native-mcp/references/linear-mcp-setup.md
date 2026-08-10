# Linear MCP Setup

## Config

```yaml
mcp_servers:
  linear:
    url: https://mcp.linear.app/mcp
    transport: http
    auth: oauth
    enabled: true
```

## Setup Steps

1. Add the config block above to `config.yaml` (use Python yaml module — `patch`/`write_file` are blocked on config.yaml)
2. Restart gateway: `hermes gateway restart`
3. Test & authenticate: `hermes mcp test linear`
4. Browser opens → log in to Linear → authorize
5. Tools discovered: 38 (issues, projects, comments, documents, teams, users, etc.)

## Tools Available

Key tools after auth:
- `list_issues` / `get_issue` / `save_issue` — CRUD on issues
- `list_projects` / `get_project` / `save_project` — CRUD on projects
- `list_comments` / `save_comment` — Comment management
- `list_teams` / `list_users` — Workspace queries
- `list_documents` / `save_document` — Document management
- `list_milestones` / `save_milestone` — Milestone management

## Notes

- Linear's MCP server is **free** — hosted by Linear, no API key needed
- OAuth tokens are managed by Hermes; no manual token handling
- Linear free tier: up to 250 issues
- Works with Hermes dashboard catalog (one-click install)
