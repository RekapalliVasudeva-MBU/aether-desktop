---
name: autonomous-coding-agents
description: "Delegate coding to CLI agents — Codex, Claude Code, OpenCo — and orchestrate autonomous coding sessions via Hermes terminal. Use when the user wants an AI coding agent (Codex, Claude Code, OpenCode, or similar CLI-based autonomous coder) to implement features, refactor code, review PRs, fix bugs, or run parallel coding work."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [coding-agent, cli, autonomous, codex, claude-code, opencode, delegation]
    related_skills: [hermes-agent]
---

# Autonomous Coding Agents

Orchestrate CLI-based AI coding agents (Codex, Claude Code, OpenCode)
through the Hermes terminal. Each agent is an autonomous CLI process that
can read files, write code, run shell commands, and manage git.

## Agent Selection

| Agent | Provider | CLI Command | Best For |
|-------|----------|-------------|----------|
| **Claude Code** | Anthropic | `claude` | Deep refactoring, complex multi-step work, subagents |
| **Codex** | OpenAI | `codex` | Fast feature implementation, batch issue fixing |
| **OpenCode** | OpenSource | `opencode` | Provider-agnostic, TUI-first workflows |

All three require `pty=true` and a git repository.

## Common Patterns

### One-Shot Tasks

| Agent | Pattern |
|-------|---------|
| Claude Code | `claude -p "task" --max-turns 10 --allowedTools "Read,Edit"` |
| Codex | `codex exec "task"` |
| OpenCode | `opencode run "task"` |

### Background Mode (Long Tasks)

Start with `background=true, pty=true`, then monitor via `process` tool:

```
terminal(command="<agent> '<task>'", workdir="~/project", background=true, pty=true)
# Returns session_id
process(action="poll", session_id="<id>")
process(action="submit", session_id="<id>", data="yes")  # answer prompts
process(action="kill", session_id="<id>")
```

### Parallel Work (Worktrees)

```bash
git worktree add -b fix/issue-78 /tmp/issue-78 main
git worktree add -b fix/issue-99 /tmp/issue-99 main
```

Then launch agents in each worktree directory.

## Claude Code — Key Details

- **Auth:** `ANTHROPIC_API_KEY` or `claude auth login`
- **Print mode (preferred for one-shots):** `claude -p "..." --max-turns 10 --allowedTools "Read,Edit"`
- **Interactive mode:** Requires tmux orchestration (see pitfalls)
- **Key flags:** `--max-turns`, `--max-budget-usd`, `--allowedTools`, `--fallback-model`, `--bare`, `--worktree`
- **PR review:** `claude -p "Review PR #42" --from-pr 42`
- **Sandbox issues in gateway context:** Use `codex exec --sandbox danger-full-access` or `claude --dangerously-skip-permissions`
- **Dialog handling:** Trust dialog → Enter; Permissions dialog → Down+Enter
- **Settings:** `.claude/settings.json` (project) or `~/.claude/settings.json` (global)
- **Memory:** `CLAUDE.md` / `.claude/CLAUDE.md`

## Codex — Key Details

- **Auth:** `OPENAI_API_KEY` or Codex OAuth (`hermes auth add openai-codex`)
- **One-shot:** `codex exec "task"`
- **Key flags:** `--full-auto`, `--yolo`, `--sandbox danger-full-access`
- **PR review:** Clone to temp, `codex review --base origin/main`
- **Parallel:** Worktrees + `codex exec --yolo` per issue
- **Gateway sandbox fix:** `codex exec --sandbox danger-full-access "<task>"`

## OpenCode — Key Details

- **Auth:** `opencode auth login`
- **One-shot:** `opencode run "task"`
- **Key flags:** `--file <path>`, `--model provider/model`, `--thinking`, `--variant high`
- **PR review:** `opencode pr 42`
- **Exit:** Ctrl+C (`\x03`) — `/exit` is NOT valid
- **Session resume:** `opencode -c` (continue last) or `opencode -s <session-id>`

## Orchestration Rules

1. **Always use `pty=true`** for interactive CLI agents
2. **Git repo required** — agents refuse to run outside a git directory
3. **Set `workdir`** to keep agents focused on the right project
4. **Set `--max-turns` in print mode** to prevent runaway loops
5. **Clean up tmux sessions** when done — `tmux kill-session -t <name>`
6. **Prefer print mode for single tasks** — cleaner, no dialog handling
7. **Use tmux for multi-turn interactive work**
8. **Parallel is fine** — run multiple agents for batch work
9. **Don't interfere** — monitor with poll/log, be patient

## Pitfalls

- Interactive mode REQUIRES PTY — agents hang without one
- `--dangerously-skip-permissions` dialog defaults to "No, exit" — send Down then Enter
- `claude --max-budget-usd` minimum is ~$0.05
- `opencode run` does NOT need pty; interactive `opencode` DOES
- OpenCode `/exit` opens agent selector — use Ctrl+C to exit
- Session resumption requires same working directory
- Claude may use `python` instead of `python3` — self-corrects
- Trust dialog appears only once per directory
- Background tmux sessions persist — always clean up

## Verification

```bash
# Claude Code
claude --version
claude auth status

# Codex
codex --version

# OpenCode
opencode --version
opencode auth list
```
