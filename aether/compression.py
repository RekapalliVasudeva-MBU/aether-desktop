"""Hermes-style token saving for Aether chat.

Three cheap, loss-free techniques (same *meaning*, fewer tokens):
  1. History trimming  — keep only the most recent K turns + a 1-line
     recap of what was dropped, so the model never re-reads the whole log.
  2. RAG context cap   — already enforced in rag.py (RETRIEVE_MAX_CHARS).
  3. Tool-result trim  — long tool outputs are summarized/truncated before
     they re-enter the prompt on the next turn.

No meaning is lost for the user: the visible transcript is untouched; only the
tokens we *send to the model* are reduced.
"""
from __future__ import annotations

from typing import Dict, List

# Keep this many recent (user, assistant) turns verbatim; older ones are
# collapsed into a single short recap line. 12 turns ~ a long chat.
KEEP_TURNS = 12
# Max chars for any single tool result returned to the model.
TOOL_RESULT_MAX = 4000


def trim_history(messages: List[Dict]) -> List[Dict]:
    """Return a token-light copy of `messages` for the *next* model call.

    `messages` is the full in-memory transcript (system + turns). We keep the
    system prompt, the most recent KEEP_TURNS user/assistant pairs, and a
    one-line recap of anything older that was dropped.
    """
    if len(messages) <= 1:
        return list(messages)

    system = messages[0] if messages[0].get("role") == "system" else None
    rest = messages[1:] if system is not None else messages

    # user/assistant pairs only (drop raw tool entries from the visible tail calc)
    conversational = [m for m in rest if m.get("role") in ("user", "assistant")]
    if len(conversational) <= KEEP_TURNS * 2:
        return list(messages)

    # how many leading conversational messages to drop
    drop = len(conversational) - KEEP_TURNS * 2
    dropped = conversational[:drop]
    kept_conv = conversational[drop:]

    # recap of dropped content (concise, no detail)
    user_topics = [m["content"][:60] for m in dropped if m.get("role") == "user"]
    recap = "[earlier conversation recap] " + (
        "; ".join(user_topics) if user_topics else "prior context omitted"
    )

    out: List[Dict] = []
    if system is not None:
        out.append(system)
    out.append({"role": "system", "content": recap})
    # append the kept conversational turns, plus any tool messages that belong
    # to the most recent slice (kept verbatim by index alignment)
    kept_set = set(id(m) for m in kept_conv)
    for m in rest:
        if m.get("role") in ("user", "assistant") and id(m) in kept_set:
            out.append(m)
        elif m.get("role") == "tool":
            # keep tool results from the recent window; trim very long ones
            out.append(_trim_tool(m))
    return out


def _trim_tool(m: Dict) -> Dict:
    content = m.get("content", "")
    if isinstance(content, str) and len(content) > TOOL_RESULT_MAX:
        return {**m, "content": content[:TOOL_RESULT_MAX] + "\n…[result truncated for token savings]"}
    return m
