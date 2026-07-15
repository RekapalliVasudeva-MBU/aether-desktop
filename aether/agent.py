"""Core Aether agent loop.

A minimal but real tool-calling agent (Hermes-style):
  - builds a system prompt from SOUL.md + USER.md + memory
  - sends messages to OpenRouter with tool schemas
  - if the model emits tool_calls, executes them and feeds results back
  - repeats up to max_turns
  - supports an optional "grounding" mode where retrieved RAG context is
    injected as the system prompt (used by the RAG mode)

This is synchronous (simple, robust, matches the OpenAI tool-call pattern).
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional

from . import config, provider, skills
from . import tools
from .tools import tool_schemas, call_tool
from .memory import Memory
from . import mcp as mcp_mod


def get_external_tool_schemas() -> List[Dict]:
    """Merge built-in tool schemas with any connected MCP server tools."""
    schemas = tool_schemas()
    try:
        clients = mcp_mod.connect_all()
        for name, client in clients.items():
            for t in client.capabilities:
                # MCP tool -> OpenAI function schema (best-effort)
                schemas.append({
                    "name": f"mcp__{name}__{t['name']}",
                    "description": t.get("description", f"MCP tool {t['name']} from {name}"),
                    "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
                })
    except Exception as e:
        print(f"[mcp] skipped: {e}")
    return schemas


def _skill_dirs() -> List[Dict]:
    """Return a list of {name, path, enabled} for each discovered skill."""
    from .skills import discover
    out = []
    for name, d in discover().items():
        out.append({"name": name, "path": str(d),
                    "enabled": config.item_enabled("skills", name, True)})
    return out


def _tool_specs() -> List[Dict]:
    """Return built-in + MCP tool specs with their enabled flag."""
    specs = []
    for name, meta in tools.TOOLS.items():
        specs.append({"name": name, "kind": "builtin",
                      "enabled": config.item_enabled("tools", name, True)})
    try:
        clients = mcp_mod.connect_all()
        for srv, client in clients.items():
            for t in client.capabilities:
                specs.append({
                    "name": f"mcp__{srv}__{t['name']}", "kind": f"mcp:{srv}",
                    "enabled": config.item_enabled("mcp", srv, True),
                })
    except Exception:
        pass
    return specs


def build_system_prompt(mode: str = "normal", rag_context: str = "") -> str:
    soul = config.read_markdown("SOUL.md")
    user = config.read_markdown("USER.md")
    mem = Memory().render_for_prompt()
    parts = []
    if soul:
        parts.append(soul)
    if user:
        parts.append(user)
    if mem:
        parts.append(mem)
    if mode == "rag" and rag_context:
        parts.append(
            "You are answering using the user's personal knowledge base. "
            "Base your answer ONLY on the retrieved context. If the answer is not "
            "in the context, say you don't have enough information.\n\n"
            f"RETRIEVED CONTEXT:\n{rag_context}"
        )
    parts.append(
        "You are an agent: when you need to run code, read/write files, search the "
        "web, or list files, call the provided tools. Do not fabricate results."
    )
    return "\n\n".join(parts)


def run_agent(
    user_message: str,
    mode: str = "normal",
    rag_context: str = "",
    model: Optional[str] = None,
    max_turns: Optional[int] = None,
    on_token: Optional[callable] = None,
) -> str:
    cfg = config.load_config()
    max_turns = max_turns or cfg["agent"]["max_turns"]
    memory = Memory()

    system = build_system_prompt(mode=mode, rag_context=rag_context)
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_message},
    ]

    schemas = get_external_tool_schemas()
    caps = config.get_capabilities()
    # respect capability toggles + per-item enable maps
    enabled_tools = {s["name"]: s["enabled"] for s in _tool_specs()}
    if not caps.get("tools", True):
        schemas = []
    else:
        schemas = [s for s in schemas if enabled_tools.get(s["name"], True)]
    if not caps.get("mcps", True):
        schemas = [s for s in schemas if not s["name"].startswith("mcp__")]
    mcp_clients = {}

    # preload relevant skill content into a system note (cheap, improves quality)
    rel = skills.find_relevant(user_message) if caps.get("skills", True) else []
    if rel:
        skill_notes = []
        for s in rel:
            txt = skills.load_skill(s)
            if txt:
                skill_notes.append(f"### Skill: {s}\n{txt[:1500]}")
        if skill_notes:
            messages[0]["content"] += "\n\nRelevant skills:\n" + "\n\n".join(skill_notes)

    turn = 0
    last_text = ""
    while turn < max_turns:
        turn += 1
        resp = provider.chat(messages, model=model, stream=False, tools=schemas)
        msg = resp.choices[0].message
        content = msg.content or ""
        tool_calls = getattr(msg, "tool_calls", None)

        if not tool_calls:
            last_text = content
            messages.append({"role": "assistant", "content": content})
            # save any durable preference the model flagged
            if "REMEMBER:" in content and caps.get("memory", True):
                fact = content.split("REMEMBER:", 1)[1].strip().splitlines()[0]
                memory.add(fact)
            if on_token:
                on_token(content)
            break

        # assistant message with tool calls
        messages.append({
            "role": "assistant",
            "content": content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in tool_calls
            ],
        })

        for tc in tool_calls:
            fn = tc.function
            try:
                args = json.loads(fn.arguments or "{}")
            except Exception:
                args = {}
            # route MCP tools vs built-in tools
            if fn.name.startswith("mcp__"):
                parts = fn.name.split("__", 2)
                srv, tname = parts[1], parts[2]
                if not mcp_clients:
                    mcp_clients = mcp_mod.connect_all()
                client = mcp_clients.get(srv)
                result = client.call(tname, args) if client else json.dumps({"error": f"no MCP server {srv}"})
            else:
                result = call_tool(fn.name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    return last_text
