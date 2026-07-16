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
    if not q:
        return json.dumps({"error": "query is required"})
    if not shutil.which("curl"):
        return json.dumps({"error": "curl not available for web search"})
    try:
        # DuckDuckGo HTML endpoint via POST form (GET/query-string is walled,
        # but a real form POST returns parseable results).
        out = subprocess.run(
            ["curl", "-s", "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
             "--data-urlencode", f"q={q}",
             "https://html.duckduckgo.com/html/"],
            capture_output=True, text=True, timeout=25,
        ).stdout
        import re as _re
        # titles + urls: <a class="result__a" href="...">title</a>
        links = _re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', out, _re.S)
        # snippets: <a class="result__snippet" ...>text</a>
        snippets = _re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', out, _re.S)
        def clean(s): return _re.sub(r"<[^>]+>", "", s).strip()
        results = []
        for i, (href, title) in enumerate(links[:5]):
            results.append({
                "title": clean(title),
                "url": href,
                "snippet": clean(snippets[i]) if i < len(snippets) else "",
            })
        return json.dumps({"query": q, "results": results, "count": len(results)})
    except Exception as e:
        return json.dumps({"error": f"web search failed: {e}"})


register(
    "web_search",
    {
        "name": "web_search",
        "description": (
            "Search the web via DuckDuckGo and return result titles, URLs, and snippets. "
            "USE THIS whenever the user asks you to search the web, look something up online, "
            "find current info, or 'add a search capability'. Returns up to 5 results."
        ),
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    _web_search,
)


# -------------------------------------------------------------------------
# MCP server management (lets the agent configure MCP servers itself)
# -------------------------------------------------------------------------
def _mcp_add_server(args: Dict) -> str:
    from . import mcp as mcp_mod
    name = (args.get("name") or "").strip()
    spec = args.get("spec") or {}
    if not name or not isinstance(spec, dict):
        return json.dumps({"ok": False, "error": "name and spec are required"})
    if "description" not in spec:
        spec["description"] = f"MCP server {name}"
    try:
        ok = mcp_mod.add_server(name, spec)
        return json.dumps({
            "ok": ok, "name": name, "spec": spec,
            "note": "MCP server added to config. Its tools (mcp__%s__*) will "
                    "appear in your schema on the next turn / new chat." % name,
        })
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


register(
    "mcp_add_server",
    {
        "name": "mcp_add_server",
        "description": (
            "Add an MCP (Model Context Protocol) server to Aether's own config so "
            "its tools become available to you. USE THIS whenever the user asks you "
            "to install/connect/add an MCP server (e.g. Playwright). "
            "stdio server: spec = {command:'npx', args:['-y','@playwright/mcp@latest'], "
            "description:'...'}. http server: spec = {url:'https://host/mcp', "
            "description:'...'}. Returns ok once written to config.yaml."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "unique server id, e.g. 'playwright'"},
                "spec": {"type": "object",
                         "description": "server spec: {command,args,description} for stdio "
                                        "OR {url,description} for http"},
            },
            "required": ["name", "spec"],
        },
    },
    _mcp_add_server,
)


def _mcp_list_servers(args: Dict) -> str:
    from . import mcp as mcp_mod
    try:
        return json.dumps({"servers": mcp_mod.list_servers()})
    except Exception as e:
        return json.dumps({"error": str(e)})


register(
    "mcp_list_servers",
    {
        "name": "mcp_list_servers",
        "description": "List the MCP servers currently configured in Aether (name, spec, enabled, use_case).",
        "parameters": {"type": "object", "properties": {}},
    },
    _mcp_list_servers,
)


def _mcp_remove_server(args: Dict) -> str:
    from . import mcp as mcp_mod
    name = (args.get("name") or "").strip()
    try:
        ok = mcp_mod.remove_server(name)
        return json.dumps({"ok": ok, "name": name})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


register(
    "mcp_remove_server",
    {
        "name": "mcp_remove_server",
        "description": "Remove an MCP server from Aether's config by name.",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    _mcp_remove_server,
)


def _mcp_test_server(args: Dict) -> str:
    from . import mcp as mcp_mod
    name = (args.get("name") or "").strip()
    try:
        return json.dumps(mcp_mod.test_connection(name))
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


register(
    "mcp_test_server",
    {
        "name": "mcp_test_server",
        "description": "Probe a configured MCP server's connection (spawns it / does a network round-trip). Returns ok + tool count or an error.",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    _mcp_test_server,
)


# -------------------------------------------------------------------------
# YouTube transcript by link (lets the agent "watch" a video's content)
# -------------------------------------------------------------------------
def _youtube_transcript(args: Dict) -> str:
    import re as _re
    url = (args.get("url") or "").strip()
    if not url:
        return json.dumps({"ok": False, "error": "url is required"})
    m = _re.search(r"(?:v=|youtu\.be/|/shorts/|/embed/)([\w-]{11})", url)
    if not m:
        return json.dumps({"ok": False, "error": "could not find an 11-char YouTube video id in the URL"})
    vid = m.group(1)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        langs = args.get("langs") or ["en"]
        try:
            tr = YouTubeTranscriptApi.get_transcript(vid, languages=langs)
        except Exception:
            tr = YouTubeTranscriptApi.get_transcript(vid)  # fall back to any lang
        text = "\n".join(seg["text"] for seg in tr)
        return json.dumps({"ok": True, "video_id": vid, "segments": len(tr),
                           "transcript": text[:20000]})
    except Exception as e:
        return json.dumps({"ok": False, "error": f"transcript unavailable: {e}"})


register(
    "youtube_transcript",
    {
        "name": "youtube_transcript",
        "description": (
            "Fetch the transcript/text of a YouTube video from its URL or link so you "
            "can read and reason about its content. Call this whenever the user pastes "
            "a YouTube link and asks you to summarize, explain, or extract info from the "
            "video. Returns the full transcript text. Optional `langs` (e.g. ['en'])."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "YouTube URL or link"},
                "langs": {"type": "array", "items": {"type": "string"},
                          "description": "preferred language codes, e.g. ['en']"},
            },
            "required": ["url"],
        },
    },
    _youtube_transcript,
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
    # Some providers return tool arguments as a JSON *string* instead of an
    # object. Normalise so handlers always receive a dict.
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {}
    if not isinstance(args, dict):
        args = {}
    try:
        return TOOLS[name]["handler"](args)
    except Exception as e:
        return json.dumps({"error": f"tool {name} crashed: {e}"})
