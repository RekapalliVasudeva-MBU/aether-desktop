"""Built-in tools for the Aether agent.

Each tool: name, schema (OpenAI function-calling format), and a handler that
returns a JSON string. The agent loop calls these based on the model's
tool_calls. This is the same pattern Hermes uses (registry + schema + handler).
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Callable, Dict, List

import aether.config as config

# In a real agent the web_search tool would call a search API. To stay
# dependency-free and offline-safe we use a simple curl to DuckDuckGo HTML
# and strip tags, but degrade gracefully if no network.
import shutil

TOOLS: Dict[str, Dict] = {}


def register(name: str, schema: Dict, handler: Callable[[Dict], str]):
    TOOLS[name] = {"schema": schema, "handler": handler}


# --------------------------------------------------------------------------
# terminal
# --------------------------------------------------------------------------
def _terminal(args: Dict) -> str:
    cmd = args.get("command", "")
    cwd = args.get("cwd") or os.getcwd()
    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=120
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return json.dumps({
            "exit_code": proc.returncode,
            "output": out[-8000:],  # cap to keep context small
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"exit_code": -1, "output": "command timed out (120s)"})
    except Exception as e:
        return json.dumps({"exit_code": -1, "output": f"error: {e}"})


register(
    "terminal",
    {
        "name": "terminal",
        "description": "Run a shell command and return its stdout/stderr. Use for builds, git, processes, file ops.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "shell command to run"},
                "cwd": {"type": "string", "description": "working directory (optional)"},
            },
            "required": ["command"],
        },
    },
    _terminal,
)


# --------------------------------------------------------------------------
# read_file
# --------------------------------------------------------------------------
def _read_file(args: Dict) -> str:
    p = Path(args.get("path", "")).expanduser()
    if not p.exists():
        return json.dumps({"error": f"file not found: {p}"})
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return json.dumps({"error": f"cannot read: {e}"})
    limit = int(args.get("limit", 2000))
    lines = text.splitlines()
    shown = "\n".join(lines[:limit])
    return json.dumps({"path": str(p), "lines": len(lines), "content": shown})


register(
    "read_file",
    {
        "name": "read_file",
        "description": "Read a text file (code, config, logs). Returns up to `limit` lines.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "limit": {"type": "integer", "default": 2000},
            },
            "required": ["path"],
        },
    },
    _read_file,
)


# --------------------------------------------------------------------------
# write_file
# --------------------------------------------------------------------------
def _write_file(args: Dict) -> str:
    p = Path(args.get("path", "")).expanduser()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(args.get("content", ""), encoding="utf-8")
        return json.dumps({"ok": True, "path": str(p)})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


register(
    "write_file",
    {
        "name": "write_file",
        "description": "Write (overwrite) a file with the given content.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    _write_file,
)


# --------------------------------------------------------------------------
# list_files
# --------------------------------------------------------------------------
def _list_files(args: Dict) -> str:
    d = Path(args.get("dir", ".")).expanduser()
    if not d.exists():
        return json.dumps({"error": f"no such dir: {d}"})
    items = []
    for it in sorted(d.iterdir()):
        items.append({"name": it.name, "type": "dir" if it.is_dir() else "file"})
    return json.dumps({"dir": str(d), "items": items[:500]})


register(
    "list_files",
    {
        "name": "list_files",
        "description": "List files/dirs in a directory.",
        "parameters": {
            "type": "object",
            "properties": {"dir": {"type": "string", "default": "."}},
            "required": [],
        },
    },
    _list_files,
)


# --------------------------------------------------------------------------
# web_search (graceful offline fallback)
# --------------------------------------------------------------------------
def _web_search(args: Dict) -> str:
    q = args.get("query", "")
    if not shutil.which("curl"):
        return json.dumps({"error": "curl not available for web search"})
    try:
        out = subprocess.run(
            ["curl", "-s", "-A", "Mozilla/5.0", f"https://html.duckduckgo.com/html/?q={q}"],
            capture_output=True, text=True, timeout=20,
        ).stdout
        # crude extraction of result titles + snippets
        import re
        snippets = re.findall(r'result__snippet"[^>]*>(.*?)</a>', out, re.S)
        titles = re.findall(r'result__a"[^>]*>(.*?)</a>', out, re.S)
        def clean(s): return re.sub(r"<[^>]+>", "", s).strip()
        results = [{"title": clean(t), "snippet": clean(s)}
                   for t, s in zip(titles, snippets)][:5]
        return json.dumps({"query": q, "results": results})
    except Exception as e:
        return json.dumps({"error": f"web search failed: {e}"})


register(
    "web_search",
    {
        "name": "web_search",
        "description": "Search the web for a query and return result titles/snippets.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    _web_search,
)


def tool_schemas() -> List[Dict]:
    return [t["schema"] for t in TOOLS.values()]


def list_tools() -> List[Dict[str, object]]:
    """Return [{name, description, enabled}] for every registered built-in tool."""
    out = []
    for name, meta in TOOLS.items():
        out.append({
            "name": name,
            "description": meta["schema"].get("description", ""),
            "enabled": config.item_enabled("tools", name, True),
        })
    return out


def delete_tool(name: str) -> bool:
    """Built-in tools can't be deleted from code; this only disables them.

    Returns True if the tool exists (and is now disabled)."""
    if name not in TOOLS:
        return False
    config.set_item_enabled("tools", name, False)
    return True


def call_tool(name: str, args: Dict) -> str:
    if name not in TOOLS:
        return json.dumps({"error": f"unknown tool: {name}"})
    try:
        return TOOLS[name]["handler"](args or {})
    except Exception as e:
        return json.dumps({"error": f"tool {name} crashed: {e}"})
