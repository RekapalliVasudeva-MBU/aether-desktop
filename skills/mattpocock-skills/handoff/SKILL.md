---
name: handoff
description: Compact the current conversation into a handoff document so another agent or session can continue the work. Use when delegating work between agents, saving progress across sessions, or when the user wants to hand off work.
---

# Handoff

Write a handoff document summarising the current conversation so a fresh agent can continue the work. Save it to a temp file path.

Suggest the skills to be used, if any, by the next session.

Do not duplicate content already captured in other artifacts (PRDs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

## Handoff Document Structure

```
# Handoff: [Task Name]

## What was done
- [completed items]

## What's next
- [pending items]

## Key decisions
- [decision 1 with reasoning]
- [decision 2 with reasoning]

## Relevant files
- [file paths modified/created]

## Recommended skills for next session
- [skill names]

## Context
[Any other important context]
```

## When to Use

- Delegating work to a subagent via `delegate_task`
- Saving progress before a session ends
- Switching between different agent tools
- Long-running projects that span multiple sessions

## Persisting the actual conversation (Hermes native export)
A *handoff doc* (above) is a summary for another agent. When the user says
"save this session" / "this conversation is important, keep it", they usually
mean the **full transcript**, not a summary. Use Hermes's native session store:

1. Find the session ID: `hermes sessions list`
   (columns: Title / Preview / Last Active / ID — e.g. `20260711_123443_faf771`).
2. Export to a PERSISTENT location the user controls — NOT `~/.hermes/sessions/`
   (that store is internal and can be pruned). Use a project folder:
   ```bash
   hermes sessions export --format jsonl --session-id 20260711_123443_faf771 \
       project_rag/session_backups/full_session.jsonl
   hermes sessions export --format md    --session-id 20260711_123443_faf771 \
       project_rag/session_backups/   # writes <id>-<slug>.md (human-readable)
   ```
   - `--format` accepts `jsonl` (full fidelity: every message + tool call — best
     for re-loading / `hermes --resume <ID>`), `md` (readable), `qmd`, `html`, `trace`.
   - A `manifest.jsonl` (SHA-256 + message_count + paths) is written alongside.
   - Verify the file is non-empty after export (e.g. `wc -c`).
3. Optionally `--upload --public` to push to a shareable paste (needs network).

The handoff doc is still the right tool when *delegating* to a subagent;
`hermes sessions export` is for *archiving the user's own conversation*. Use both
when you need to hand off AND preserve the original.
