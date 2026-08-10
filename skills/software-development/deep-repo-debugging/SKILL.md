---
name: deep-repo-debugging
description: "Systematic multi-repo debugging workflow: trace errors across related codebases via git diffs, logs, and code search."
version: 1.0.0
author: valte
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, multi-repo, root-cause, git, logs, code-search]
    category: software-development
---

# Deep Multi-Repo Debugging

When an error spans multiple related repositories (e.g., Hermes Agent + project_rag + Aether desktop app), follow this workflow to trace the root cause without guessing.

## When to Use

- Error mentions components from multiple projects
- "Works locally, fails in production" across services
- User reports regressions after your changes
- Timeout/connection errors between services

## Workflow

### 1. Inventory All Repositories

```bash
# List all relevant project directories
ls -la /c/Users/valte/ | grep -E "hermes|project_rag|aether"

# Check git status on each
for dir in hermes-agent project_rag aether; do
  echo "=== $dir ==="
  cd /c/Users/valte/$dir && git status
done
```

### 2. Capture Baseline: What Changed?

```bash
# For each repo, get recent commits and working tree changes
git log --oneline -10
git diff --name-only
git diff  # full diff for modified files
```

**Key insight:** The user's "what issues u created yesterday" question maps directly to `git diff` output across all repos.

### 3. Search for the Error Signature

```bash
# Search for the exact error string across all repos
grep -r "model.options" /c/Users/valte/hermes/hermes-agent --include="*.py" --include="*.ts" --include="*.tsx"
grep -r "model.options" /c/Users/valte/project_rag --include="*.py" --include="*.html"
grep -r "model.options" /c/Users/valte/aether --include="*.py" --include="*.html"

# Also search logs
grep -i "model.options" /c/Users/valte/AppData/Local/hermes/logs/*.log
```

### 4. Trace the Call Chain

For "model.options timeout":
1. **Frontend** (desktop/web): `requestModelOptions()` → `gateway.request('model.options', params)`
2. **Gateway** (tui_gateway): `@method("model.options")` handler → `build_models_payload()`
3. **Backend** (hermes_cli/web_server): `@app.get("/api/model/options")` → `build_models_payload()`
4. **Inventory** (hermes_cli/inventory): `build_models_payload()` → provider catalogs, pricing, auth probes

### 5. Check Timeout Configurations

```bash
# Search for timeout settings in the call chain
grep -rn "timeout" /c/Users/valte/AppData/Local/hermes/hermes-agent/tui_gateway/server.py
grep -rn "timeout" /c/Users/valte/AppData/Local/hermes/hermes-agent/hermes_cli/web_server.py
grep -rn "timeout" /c/Users/valte/AppData/Local/hermes/hermes-agent/hermes_cli/inventory.py
```

### 6. Correlate with Logs

```bash
# Check gateway logs for the exact request
grep -B5 -A5 "model.options" /c/Users/valte/AppData/Local/hermes/logs/gateway.log

# Check for ConnectTimeout (common when probing providers)
grep -i "ConnectTimeout" /c/Users/valte/AppData/Local/hermes/logs/gateway.log
```

### 7. Verify the Fix Path

Once you identify the bottleneck (e.g., `probe_custom_providers=True` hitting slow API):
- Check if `refresh` param is being passed unnecessarily
- Verify `probe_current_custom_provider` logic
- Consider caching TTL (1 hour default)

## Applied Example: "model.options timeout" (This Session)

**Error:** "Hermes dashboard request timed out: model.options"

**Trace:**
1. Desktop app calls `model.options` via JSON-RPC to tui_gateway
2. tui_gateway calls `build_models_payload(..., refresh=bool(params.get("refresh")), probe_custom_providers=bool(params.get("refresh")))`
3. When `refresh=true`, it probes ALL custom providers' `/models` endpoints
4. If any provider is slow/unreachable → ConnectTimeout → request fails

**Root cause found in logs:** `httpx.ConnectTimeout` from Telegram platform (unrelated but same symptom pattern)

**Fix approach:** Don't pass `refresh=true` on initial model picker load; only on explicit "Refresh Models" button click.

## Pitfalls to Avoid

- ❌ Searching only one repo when error spans services
- ❌ Fixing the symptom (increase timeout) instead of cause (unnecessary probe)
- ❌ Not checking git diff first — user's "what did you break" = your working tree changes
- ❌ Ignoring logs because "it works locally" — production has network latency

## Tooling Checklist

- [ ] `git status` + `git diff` on all repos
- [ ] `grep -r` for error signature across all repos
- [ ] Log correlation (gateway.log, agent.log, server.log)
- [ ] Trace the exact call chain from UI → API → backend
- [ ] Identify where timeouts are configured (or missing)
- [ ] Test fix with `refresh=false` (default) vs `refresh=true` (explicit)