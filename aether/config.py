"""Aether configuration: YAML + SOUL/USER markdown + environment secrets.

Paths follow a Hermes-style profile layout (each profile is isolated):
  AETHER_HOME (default %APPDATA%/aether)  -> config.yaml, SOUL.md, USER.md,
  memory/, skills/, sessions/, logs/, mcp/
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

# --- home / profile handling (mirrors Hermes get_hermes_home pattern) ---
if os.environ.get("AETHER_HOME"):
    AETHER_HOME = Path(os.environ["AETHER_HOME"]).expanduser()
else:
    AETHER_HOME = Path(os.environ.get("APPDATA", Path.home())) / "aether"


def ensure_dirs() -> None:
    for sub in ("", "memory", "skills", "sessions", "logs", "mcp"):
        (AETHER_HOME / sub).mkdir(parents=True, exist_ok=True)


# --- defaults ---
DEFAULT_CONFIG: Dict[str, Any] = {
    "model": {
        "provider": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "default": "openrouter/free",
        "api_mode": "chat_completions",
        "max_tokens": 4096,
        "temperature": 0.7,
    },
    "agent": {
        "max_turns": 90,
        "system": "auto",
        "tool_use_enforcement": "auto",
        "parallel_tool_calls": True,
    },
    "memory": {"enabled": True, "path": "memory/memory.jsonl"},
    "skills": {"enabled": True, "dirs": ["skills", "~/.aether/skills"]},
    "mcp": {"servers": {}},
    "telegram": {"enabled": False, "token": "", "poll": True},
    # capability toggles (user can turn these on/off in the desktop UI)
    "capabilities": {
        "skills": True,
        "tools": True,
        "mcps": True,
        "memory": True,
        "rag": True,
    },
    "rag": {
        "enabled": True,
        # Portable default: a vector DB under AETHER_HOME. Set RAG_DB_PATH env
        # or override in config.yaml to point at a prebuilt collection.
        "chromadb_path": os.environ.get("RAG_DB_PATH", str(AETHER_HOME / "rag_vector_db")),
        "collection": "docling_knowledge_base",
        "n_results": 6,
    },
    "logging": {"level": "INFO"},
}


def _deep_merge(base: Dict, override: Dict) -> Dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config() -> Dict[str, Any]:
    ensure_dirs()
    cfg_path = AETHER_HOME / "config.yaml"
    user_cfg: Dict[str, Any] = {}
    if cfg_path.exists():
        try:
            import yaml
            user_cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            print(f"[warn] could not parse config.yaml: {e}")
    return _deep_merge(DEFAULT_CONFIG, user_cfg)


def save_config(cfg: Dict[str, Any]) -> None:
    ensure_dirs()
    try:
        import yaml
        (AETHER_HOME / "config.yaml").write_text(
            yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
    except Exception as e:
        print(f"[warn] could not write config.yaml: {e}")


# --- secrets (env only; never written to config.yaml per Hermes rules) ---
# SECURITY: Aether NEVER reads the user's personal Hermes .env or any path
# containing a username. Distributable code must not leak the developer's key.
# Key resolution order:
#   1) OPENROUTER_API_KEY env var        (best — user sets their OWN)
#   2) AETHER_HOME/.env  (aether's OWN secret file, written by `aether doctor --fix`)
def get_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    own_env = AETHER_HOME / ".env"
    if own_env.exists():
        for line in own_env.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip().startswith("OPENROUTER_API_KEY="):
                v = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                if v:
                    return v
    return ""


def set_api_key(key: str) -> None:
    """Write the user's OWN OpenRouter key into Aether's .env (AETHER_HOME/.env)."""
    own_env = AETHER_HOME / ".env"
    AETHER_HOME.mkdir(parents=True, exist_ok=True)
    lines = []
    if own_env.exists():
        lines = [l for l in own_env.read_text(encoding="utf-8").splitlines()
                 if not l.startswith("OPENROUTER_API_KEY=")]
    lines.append(f"OPENROUTER_API_KEY={key.strip()}")
    own_env.write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_capability(name: str, enabled: bool) -> bool:
    """Toggle a capability (skills/tools/mcps/memory/rag). Returns new state."""
    cfg = load_config()
    if name not in cfg["capabilities"]:
        return False
    cfg["capabilities"][name] = bool(enabled)
    save_config(cfg)
    return bool(enabled)


def get_capabilities() -> Dict[str, bool]:
    return dict(load_config()["capabilities"])


# --- SOUL.md / USER.md ---
def read_markdown(name: str) -> str:
    p = AETHER_HOME / name
    return p.read_text(encoding="utf-8") if p.exists() else ""


def write_markdown(name: str, content: str) -> None:
    ensure_dirs()
    (AETHER_HOME / name).write_text(content, encoding="utf-8")


def build_soul_default() -> str:
    return (
        "# SOUL.md - Aether's identity\n\n"
        "You are **Aether**, a personal AI agent and RAG assistant. "
        "You are helpful, direct, and efficient. You have two modes:\n"
        "1. **Normal** - a general agent with tools, skills, memory, and MCP integrations.\n"
        "2. **RAG** - grounded on the user's personal PDF knowledge base.\n\n"
        "You improve over time by saving reusable procedures as skills and remembering "
        "durable user preferences in memory. You never fabricate tool results. When a task "
        "needs real execution, you use tools rather than describing it.\n"
    )


def build_user_default() -> str:
    return (
        "# USER.md - About the user\n\n"
        "- Prefers concise, on-topic responses.\n"
        "- Wants shippable, simple deliverables over technical depth.\n"
        "- Values clear working / broken / pending status reports.\n"
    )


def ensure_persona_files() -> None:
    ensure_dirs()
    if not (AETHER_HOME / "SOUL.md").exists():
        write_markdown("SOUL.md", build_soul_default())
    if not (AETHER_HOME / "USER.md").exists():
        write_markdown("USER.md", build_user_default())
