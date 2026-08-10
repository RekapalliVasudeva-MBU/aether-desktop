# Session 2026-07-25: Model Options Timeout Investigation

## The Error

User reported: "Hermes dashboard request timed out: model.options"

## What This Is

`model.options` is a JSON-RPC method on `tui_gateway/server.py` (line 12383) and a REST endpoint `/api/model/options` on `hermes_cli/web_server.py` (line 5121). It's used by:
- TUI (terminal UI) model picker
- Desktop app model picker  
- Dashboard Models page

## How It Works

```python
@method("model.options")
def _(rid, params: dict) -> dict:
    ctx = load_picker_context().with_overrides(
        current_provider=getattr(agent, "provider", "") if agent else "",
        current_model=((getattr(agent, "model", "") if agent else "") or _resolve_model()),
        current_base_url=getattr(agent, "base_url", "") if agent else "",
    )
    payload = build_models_payload(
        ctx,
        explicit_only=bool(params.get("explicit_only")),
        include_unconfigured=bool(params.get("include_unconfigured")),
        picker_hints=True,
        canonical_order=True,
        pricing=True,
        capabilities=True,
        refresh=bool(params.get("refresh")),
        probe_custom_providers=bool(params.get("refresh")),
        probe_current_custom_provider=not bool(params.get("refresh")),
    )
    return _ok(rid, payload)
```

## Why It Times Out

The `build_models_payload` function (in `hermes_cli/inventory.py`) calls `probe_custom_providers` and `probe_current_custom_provider` which make **live HTTP calls to provider APIs** (OpenRouter, Anthropic, etc.) to fetch model catalogs. These network calls:

1. Can be slow (5-30s depending on provider)
2. Have no configurable timeout in the current code
3. Block the JSON-RPC response until complete
4. The dashboard/TUI waits for the full payload before rendering

## Root Cause (Likely)

The timeout is almost certainly **provider API latency** — specifically OpenRouter's `/api/v1/models` endpoint or Anthropic's model listing — not a bug in Hermes itself. The `refresh=true` parameter forces re-probing all providers.

## Fix Options

### 1. Add Timeout to Provider Probes (Recommended)
In `hermes_cli/inventory.py`, wrap provider API calls with `httpx.Timeout`:

```python
async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
    resp = await client.get("https://openrouter.ai/api/v1/models")
```

### 2. Cache Provider Catalogs Longer
Increase the 1-hour disk cache TTL for provider model lists.

### 3. Make `refresh` Default to False
Dashboard/TUI should default to cached data; only refresh on explicit user action.

### 4. Parallelize Provider Probes
Currently probes may run sequentially; use `asyncio.gather()` for parallel calls.

## What I Checked

- ✅ Local server health (`http://localhost:8000/api/health`) — works
- ✅ Named tunnel connection — works (connected to Cloudflare PoPs)
- ❌ `https://aether-rag.cfargotunnel.com` — doesn't work (no Public Hostname in Dashboard)
- ❌ `model.options` RPC — not tested directly but likely provider API timeout

## Next Steps

1. If user owns a domain: Configure Public Hostname in Cloudflare Zero Trust Dashboard → named tunnel works
2. If user needs immediate access: Use quick tunnel (`cloudflared tunnel --url http://localhost:8000`)
3. For `model.options` timeout: Patch `inventory.py` to add request timeouts and better caching