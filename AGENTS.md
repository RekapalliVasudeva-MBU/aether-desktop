# AGENTS.md — Aether

Instructions for AI coding agents working on the Aether desktop app.

## What Aether is

Aether is a desktop AI agent app: a FastAPI backend (`desktop_app.py`) served into a
pywebview (WebView2) window. It wraps an LLM agent loop (`aether/agent.py`) with
tools (`aether/tools.py`), a skill/prompt registry (`aether/skills.py`), ChromaDB
RAG (`aether/rag.py`, `aether/pdf_store.py`), context compression
(`aether/compression.py`), memory (`aether/memory.py`), an MCP client
(`aether/mcp.py`), and optional external gateway control (`aether/gateway_ctl.py`,
`aether/telegram.py`).

It ships as a frozen Windows executable via PyInstaller (`Aether.spec`) + Inno Setup
(`make_installer.py`, `aether_setup.iss`). Latest: see `CHANGELOG.md`.

## Build / run

```bash
pip install -r requirements.txt      # or uv
python desktop_app.py                 # dev server + window on :8732
python aether_cli.py --help           # CLI
```

Frozen build: `pyinstaller Aether.spec` then `python make_installer.py`.
**Frozen-build pitfall:** bundled pywebview `create_window()` has NO `icon` kwarg
(icon comes from the PyInstaller `--icon`); `desktop_app.py` must `import sys`. A dev
import check passes but the frozen exe throws — run the built exe to verify a launch fix.

## Engineering discipline

Follow `ENGINEERING.md` (plan → review → ship). Key rules:

- **Root cause only.** No fix without diagnosing the *why*.
- **Boil the Ocean.** Complete coverage; fix the whole thing, not the demo path.
- **Bisectable commits.** One logical change per commit.
- **Never force-push.** Regular `git push` only.
- **Secret scan before push.** No API keys/tokens in diffs.
- **Verify before claiming done.** Fresh test/smoke evidence required.

## Structure notes

- `aether/` is the importable package. `desktop_app.py` is the entry point.
- Build dirs (`build/`, `dist/`, `dist_build/`, `build_aether/`) and `*.log` are
  artifacts — do not edit or commit them.
- `chromadb_pkg/` is a vendored ChromaDB; treat as third-party, avoid editing.
- `aether/compression.py` caps tool output (32KB Snip) + preserves last N messages —
  preserve this contract when touching the agent loop.
