"""Aether configuration: YAML + SOUL/USER markdown + environment secrets.

Paths follow a Hermes-style profile layout (each profile is isolated):
  AETHER_HOME (default %APPDATA%/aether)  -> config.yaml, SOUL.md, USER.md,
  memory/, skills/, sessions/, logs/, mcp/
"""
from __future__ import annotations

import os
import sys
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
        "reasoning_level": "auto",  # auto|minimal|low|standard|high|max
    },
    "agent": {
        "max_turns": 90,
        "system": "auto",
        "tool_use_enforcement": "auto",
        "parallel_tool_calls": True,
    },
    "memory": {"enabled": True, "path": "memory/memory.jsonl"},
    "skills": {"enabled": True, "dirs": ["skills", "~/.aether/skills"]},
    # Per-item enable/disable maps. A missing key = enabled by default.
    "skills_enabled": {},   # {skill_name: bool}
    "tools_enabled": {},    # {tool_name: bool}
    "mcp_enabled": {},      # {server_name: bool}
    "mcp": {"servers": {}},
    "telegram": {"enabled": False, "token": "", "poll": True, "mode": "normal"},
    # Provider options the user can switch between in the UI.
    "providers": {
        "active": "openrouter",
        "options": {
            "openrouter": {
                "name": "OpenRouter",
                "base_url": "https://openrouter.ai/api/v1",
                "default": "openrouter/free",
                "api_mode": "chat_completions",
            },
            "openai": {
                "name": "OpenAI",
                "base_url": "https://api.openai.com/v1",
                "default": "gpt-4o-mini",
                "api_mode": "chat_completions",
            },
            "ollama": {
                "name": "Ollama (local)",
                "base_url": "http://localhost:11434/v1",
                "default": "llama3",
                "api_mode": "chat_completions",
            },
        },
    },
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
        # Precedence for the vector DB location:
        #   1) RAG_DB_PATH env var (explicit override)
        #   2) a bundled rag_vector_db folder next to the executable
        #      (the installer ships the prebuilt DB here so RAG works out of
        #      the box with zero config)
        #   3) AETHER_HOME/rag_vector_db (default user data dir)
        "_rag_db_bundled": str(Path(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))).parent / "rag_vector_db")
            if getattr(sys, "_MEIPASS", None)
            else str(Path(os.path.dirname(os.path.abspath(sys.argv[0])) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))).parent / "rag_vector_db"),
        "chromadb_path": os.environ.get(
            "RAG_DB_PATH",
            str(Path(os.path.dirname(os.path.abspath(sys.argv[0])) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))).parent / "rag_vector_db")
            if os.path.isdir(str(Path(os.path.dirname(os.path.abspath(sys.argv[0])) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))).parent / "rag_vector_db"))
            else str(AETHER_HOME / "rag_vector_db"),
        ),
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


# --- per-item enable/disable (skills / tools / mcp) ---
def item_enabled(kind: str, name: str, default: bool = True) -> bool:
    """kind in {'skills','tools','mcp'}. Missing key => default enabled."""
    cfg = load_config()
    table = cfg.get(f"{kind}_enabled", {})
    return bool(table.get(name, default))


def set_item_enabled(kind: str, name: str, enabled: bool) -> bool:
    cfg = load_config()
    table = cfg.setdefault(f"{kind}_enabled", {})
    table[name] = bool(enabled)
    save_config(cfg)
    return bool(enabled)


# --- providers ---
def get_providers() -> Dict[str, Any]:
    return dict(load_config()["providers"])


def set_active_provider(key: str) -> bool:
    cfg = load_config()
    if key not in cfg["providers"]["options"]:
        return False
    cfg["providers"]["active"] = key
    # keep model default in sync with the provider's default
    opt = cfg["providers"]["options"][key]
    cfg["model"]["provider"] = key
    cfg["model"]["base_url"] = opt["base_url"]
    cfg["model"]["default"] = opt["default"]
    save_config(cfg)
    return True


# --- telegram gateway config ---
def set_telegram_token(token: str) -> None:
    cfg = load_config()
    cfg["telegram"]["token"] = token.strip()
    cfg["telegram"]["enabled"] = bool(token.strip())
    save_config(cfg)


def set_telegram_mode(mode: str) -> None:
    cfg = load_config()
    cfg["telegram"]["mode"] = mode if mode in ("normal", "rag") else "normal"
    save_config(cfg)


# --- reasoning level (chat option) ---
def get_reasoning_level() -> str:
    return str(load_config()["model"].get("reasoning_level", "auto"))


def set_reasoning_level(level: str) -> str:
    allowed = ("auto", "minimal", "low", "standard", "high", "max")
    if level not in allowed:
        level = "auto"
    cfg = load_config()
    cfg["model"]["reasoning_level"] = level
    save_config(cfg)
    return level


# --- PDF drop-in directory ---
def pdf_watch_dir() -> Path:
    """Folder where the user can paste PDFs; RAG ingests them on startup/refresh."""
    d = AETHER_HOME / "rag_pdfs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def index_pdf_watch_dir() -> Dict[str, Any]:
    """Ingest any new PDFs dropped into the watch dir that aren't already indexed."""
    from . import pdf_store
    wd = pdf_watch_dir()
    indexed = set(pdf_store.list_pdfs())
    added = 0
    chunks = 0
    for p in sorted(wd.glob("*.pdf")):
        if str(p) in indexed:
            continue
        r = pdf_store.add_pdf(str(p))
        if r.get("ok"):
            added += 1
            chunks += r.get("chunks", 0)
    return {"ok": True, "added": added, "chunks": chunks, "dir": str(wd)}


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
