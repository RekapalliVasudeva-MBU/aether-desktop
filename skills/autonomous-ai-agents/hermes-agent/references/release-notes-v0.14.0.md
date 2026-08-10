# Hermes Agent v0.14.0 — "The Foundation Release" (May 16, 2026)

Since v0.13.0: 808 commits · 633 merged PRs · 1393 files changed · 545 issues closed (12 P0, 50 P1) · 215 community contributors.

## New Tools
- **`computer_use`** — macOS desktop automation via cua-driver (screenshots SOM/vision/AX, click, drag, scroll, type, key, wait, list_apps, focus_app). **macOS only** — requires cua-driver on $PATH. Does NOT steal cursor/focus. Works with any tool-capable model (not just Anthropic).
- **`x_search`** — first-class X/Twitter search with OAuth or API key auth.
- **`video_generate`** — unified pluggable video generation.

## New Integrations
- **SuperGrok OAuth** — use Grok inside Hermes with xAI account (no API key). grok-4.3 → 1M context window.
- **Microsoft Teams** — full end-to-end (Graph auth + webhook listener + pipeline runtime + outbound delivery).
- **LINE + SimpleX Chat** — 22 messaging platforms total.
- **OpenAI-compatible local proxy** — turn OAuth providers (Claude Pro, ChatGPT Pro, SuperGrok) into endpoints for Codex/Aider/Cline/Continue.
- **Zed ACP Registry** integration via `uvx`.
- **HuggingFace skills** as a trusted default tap.

## Web Dashboard
- `hermes dashboard` launches browser UI at `http://127.0.0.1:9119`.
- Install: `pip install 'hermes-agent[web]'` (FastAPI + Uvicorn).
- Pages: Status, Chat (embedded TUI — WSL2/POSIX only), Config editor, Sessions, Cron, Skills, Logs.
- Native Windows: everything works except `/chat` tab (needs POSIX PTY).

## Performance
- Cold-start ~19 seconds faster.
- Browser CDP calls **180x faster**.
- LSP semantic diagnostics on every file write.
- Cross-session 1-hour Claude prompt caching.

## New Slash Commands
- **`/handoff`** — transfer sessions live between agents.
- Native button UI for `clarify` on Telegram and Discord.
- Discord channel history backfill.

## Other
- Native Windows is now in **beta** (was early beta).
- `pip install hermes-agent` works from PyPI.
- 9 new optional skills.
- OpenRouter Pareto Code router.
- Massive debloating — lazy-install for heavyweight backends.

## Update
```bash
hermes update
```
Or from gateway chat: `/update`
