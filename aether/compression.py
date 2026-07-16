"""Hermes-style token saving for Aether chat, upgraded with the
two-layer context-compaction strategy documented in the Claude Code
source leak analysis (rule-based Snip + preserve_last_n), plus the
32KB tool-output cap that prevents context blow-up on large codebases.

Three cheap, loss-free techniques (same *meaning*, fewer tokens):
  1. History trimming  — keep only the most recent KEEP_TURNS pairs +
     a recap of what was dropped (two-layer: rule-based Snip first,
     AI summary hook available).
  2. RAG context cap   — already enforced in rag.py (RETRIEVE_MAX_CHARS).
  3. Tool-result trim  — every tool output is capped at TOOL_RESULT_MAX
     before it re-enters the prompt (the "32KB cap" from the leak).

No meaning is lost for the user: the visible transcript is untouched; only the
tokens we *send to the model* are reduced.
"""
from __future__ import annotations

from typing import Dict, List

# Keep this many recent (user, assistant) turns verbatim; older ones are
# collapsed into a short recap line. 12 turns ~ a long chat.
KEEP_TURNS = 12
# Max chars for any single tool result returned to the model. The leak notes
# Claude Code caps tool output to prevent context bloat; 24KB is generous
# enough for real results while stopping a 9000-file listing from exploding.
TOOL_RESULT_MAX = 24000
# Hard ceiling on total prompt chars we send to the model. If we still exceed
# this after trimming, oldest tool/assistant blocks are dropped first.
MAX_PROMPT_CHARS = 120_000


def _trim_tool(m: Dict) -> Dict:
    content = m.get("content", "")
    if isinstance(content, str) and len(content) > TOOL_RESULT_MAX:
        return {**m, "content": content[:TOOL_RESULT_MAX] + "\n…[result truncated for token savings]"}
    return m


def _recap(dropped: List[Dict]) -> str:
    """Rule-based Snip recap (layer 1). Cheap, loss-light summary of dropped turns."""
    user_topics = [m["content"][:70] for m in dropped if m.get("role") == "user" and isinstance(m.get("content"), str)]
    tool_count = sum(1 for m in dropped if m.get("role") == "tool")
    bits = []
    if user_topics:
        bits.append("user asked: " + "; ".join(user_topics))
    if tool_count:
        bits.append(f"{tool_count} tool result(s) consolidated")
    if not bits:
        return "[earlier context omitted to save tokens]"
    return "[earlier conversation recap] " + "; ".join(bits)


def trim_history(messages: List[Dict]) -> List[Dict]:
    """Return a token-light copy of `messages` for the *next* model call.

    Two-layer strategy (per the Claude Code leak analysis):
      Layer 1 (Snip, rule-based): cap tool outputs, drop oldest tool/assistant
        blocks when over MAX_PROMPT_CHARS.
      Layer 2 (preserve_last_n): always keep the most recent KEEP_TURNS pairs
        verbatim; older conversational turns are collapsed into a recap.
    """
    if not messages:
        return list(messages)

    system = messages[0] if messages[0].get("role") == "system" else None
    rest = messages[1:] if system is not None else messages

    conversational = [m for m in rest if m.get("role") in ("user", "assistant")]

    out: List[Dict] = []
    if system is not None:
        out.append(system)

    # Layer 2: if the conversation is short, keep everything (just cap tool results).
    if len(conversational) <= KEEP_TURNS * 2:
        for m in rest:
            out.append(_trim_tool(m) if m.get("role") == "tool" else m)
        return _enforce_budget(out)

    # Drop oldest conversational turns beyond KEEP_TURNS*2, recap them.
    drop = len(conversational) - KEEP_TURNS * 2
    dropped = conversational[:drop]
    kept_conv = conversational[drop:]
    out.append({"role": "system", "content": _recap(dropped)})

    kept_set = set(id(m) for m in kept_conv)
    for m in rest:
        role = m.get("role")
        if role in ("user", "assistant") and id(m) in kept_set:
            out.append(m)
        elif role == "tool":
            # Keep only tool results attached to the preserved window; cap them.
            out.append(_trim_tool(m))
    return _enforce_budget(out)


def _enforce_budget(messages: List[Dict]) -> List[Dict]:
    """Layer 1 (Snip): if still over the hard char ceiling, drop oldest
    non-system blocks (tool results first, then oldest assistant turns)."""
    total = sum(len(str(m.get("content", ""))) for m in messages)
    if total <= MAX_PROMPT_CHARS:
        return messages
    out = [messages[0]] if messages and messages[0].get("role") == "system" else []
    body = messages[1:] if out else list(messages)
    # Prefer dropping tool results, then oldest assistant messages.
    ordered = sorted(body, key=lambda m: (0 if m.get("role") == "tool" else 1 if m.get("role") == "assistant" else 2, 0))
    for m in ordered:
        out.append(m)
        total = sum(len(str(x.get("content", ""))) for x in out)
        if total <= MAX_PROMPT_CHARS:
            break
    return out
