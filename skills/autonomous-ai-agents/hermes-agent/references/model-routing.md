# Model Routing: Multi-Provider Setup

## Pattern: Default + Fallback + Complex Task Escalation

When the user has subscriptions to multiple providers (e.g., OpenRouter free tier + Gemini Pro), configure routing so:
- Everyday tasks use the free/cheap default
- Complex/reasoning-heavy tasks use the powerful subscribed model
- Failover is automatic if the primary provider is down

## Config

Store in `~/.hermes/config.yaml`:

```yaml
model:
  default: "openrouter/owl-alpha"       # everyday tasks (free)
  fallback: "gemini/gemini-2.5-pro"     # auto-failover + complex tasks
  providers:
    gemini:
      model: "gemini-2.5-pro"
secrets:
  gemini:
    api_key: "AQ.Ab8..."                 # API key in secrets
```

Also store the API key in `~/.hermes/.env`:
```
GEMINI_API_KEY=AQ.Ab8...
```

## CLI Commands

```bash
# Set default model
hermes config set model.default "openrouter/owl-alpha"

# Set fallback model
hermes config set model.fallback "gemini/gemini-2.5-pro"

# Set Gemini provider model
hermes config set model.providers.gemini.model "gemini-2.5-pro"

# Store API key in config secrets
hermes config set secrets.gemini.api_key "<full-key>"

# Verify
hermes config show
```

## How It Works

| Scenario | Model Used |
|---|---|
| Normal chat | openrouter/owl-alpha |
| OpenRouter fails/down | Auto-switches to gemini/gemini-2.5-pro |
| User requests complex task | Route to gemini/gemini-2.5-pro |

## Complexity-Based Coding Model Routing

**This is the preferred pattern for coding-heavy sessions.** When the user has MiniMax M2.5 (or another coding-optimized model) available via OpenRouter:

```yaml
model:
  default: "openrouter/owl-alpha"           # everyday tasks
  fallback: "openrouter/owl-alpha"          # same as default
  provider: openrouter
  complexity_routing: true                  # ENABLE auto-routing
  min_coding_score: 0.65                    # threshold for coding tasks

delegation:
  model: "minimax/minimax-m2.5:free"        # coding/subagent tasks
  provider: openrouter
```

**CRITICAL: `complexity_routing: false` means the coding model is NEVER auto-selected.** If the user says "use MiniMax for coding" or "I configured MiniMax but it's not being used", check this setting:

```bash
# Check current value
hermes config get agent.complexity_routing

# Enable auto-routing
hermes config set agent.complexity_routing true

# Verify
hermes config show | grep complexity_routing
```

When `complexity_routing: true`, Hermes uses the model catalog (`model_catalog.enabled: true`) to score tasks. Tasks scoring above `min_coding_score: 0.65` are automatically routed to the delegation model (MiniMax M2.5).

**User frustration signal**: If the user says something like "I configured MiniMax but you're not using it" or "if you can't code properly use MiniMax", the first thing to check is `complexity_routing`. It's often set to `false` by default.

## Obsidian Vault Path

The obsidian skill uses `OBSIDIAN_VAULT_PATH` env var or defaults to `~/Documents/Obsidian Vault`. To set a custom vault path:

```bash
hermes config set env.OBSIDIAN_VAULT_PATH "C:\\Users\\valte\\Documents\\Obsidian-Vault"
```

**Note**: The default path has a space ("Obsidian Vault"). If the user's vault name has a hyphen ("Obsidian-Vault"), the default won't match — you MUST set the env var.

Verify the obsidian skill picks it up:
```bash
hermes config get env.OBSIDIAN_VAULT_PATH
```

## Testing the Connection

```bash
# List available Gemini models (verifies API key works)
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=<KEY>"
```

Expected: JSON with gemini-2.5-pro, gemini-2.5-flash, gemini-2.0-flash, all with 1M context.

## Important Notes

- `hermes auth` does NOT support gemini — it supports: add, list, remove, reset, status, logout, spotify only
- Google Gemini uses `GEMINI_API_KEY` or `GOOGLE_API_KEY` env var
- Plugin `model-providers/gemini` must be enabled: `hermes plugins enable model-providers/gemini`
- Changes take effect on next session, not mid-conversation
- Fallback only triggers on failure; for complexity-based routing, agent must switch models when detecting complex tasks
