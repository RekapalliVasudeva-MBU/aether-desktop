---
name: antigravity
description: "Use Google Antigravity CLI (agy) as a subagent tool for coding tasks. When the user explicitly asks to 'use antigravity' or 'use agy' for a task, delegate it to the Antigravity CLI instead of Hermes' own tools."
metadata:
  hermes:
    tags: [antigravity, agy, google, coding-agent, subagent, cli]
    version: "1.1.0"
---

# Antigravity CLI Skill

Google Antigravity CLI (`agy`) is a terminal-first agent that runs on Gemini 3.5 Flash (free). It can code, debug, build projects, run shell commands, and manage subagents.

## Binary Location
```
C:\Users\valte\AppData\Local\agy\bin\agy.exe
```

Add to PATH: `C:\Users\valte\AppData\Local\agy\bin`

## When to Use

**Use Antigravity when:**
- User explicitly says "use antigravity" or "use agy" for a task
- User asks for a heavy coding/build task and wants it delegated to an external agent
- User wants to assign a project folder to an autonomous agent

**Do NOT use Antigravity when:**
- Task is simple (single file creation, quick edits) — use Hermes tools directly
- User doesn't mention it explicitly — default to Hermes' own capabilities
- Task requires Hermes-specific tools (browser, Telegram, WhatsApp, etc.)

## How to Invoke

### Key Flags

| Flag | Purpose |
|------|---------|
| `--print` or `--prompt` | Non-interactive mode — send prompt and get output |
| `--dangerously-skip-permissions` | Auto-approve all tool permission requests (needed for unattended use) |
| `--add-dir <path>` | Add a project directory the agent can access (repeatable) |
| `--continue` | Continue the most recent conversation |
| `--conversation <id>` | Resume a specific conversation |
| `--log-file <path>` | Write debug log to file |

### Basic Usage

**Simple prompt (non-interactive):**
```bash
export PATH="$PATH:/c/Users/valte/AppData/Local/agy/bin"
agy --print --dangerously-skip-permissions "Create a Python calculator"
```

**With project directory:**
```bash
export PATH="$PATH:/c/Users/valte/AppData/Local/agy/bin"
agy --print --dangerously-skip-permissions --add-dir C:\Users\valte\my-project "Build a REST API with authentication"
```

**Interactive session:**
```bash
export PATH="$PATH:/c/Users/valte/AppData/Local/agy/bin"
agy --prompt-interactive --dangerously-skip-permissions "Refactor this codebase to use async/await"
```

## ⚠️ CRITICAL: Output Handling

**`--print` mode does NOT return output via stdout/stderr pipes.** agy writes directly to the console terminal. When called through Hermes `terminal()`, the output appears empty. Solutions:

1. **Use `--log-file`** and then read the log:
```bash
agy --print --dangerously-skip-permissions --log-file C:\Users\valte\task.log "your prompt"
# Then read C:\Users\valte\task.log
```

2. **Use interactive mode** via `terminal(background=true, pty=true)`:
```
terminal(command="export PATH=... && agy --prompt-interactive --dangerously-skip-permissions", background=true, pty=true)
// Then use process(action='write') to send the prompt
// Use process(action='log') to read output
```

3. **Read agy's output log** after the task completes — agy logs all API calls and responses.

**Pitfall:** Do NOT rely on `terminal()` return value for agy output. Always use `--log-file` or interactive PTY mode.

## Authentication

- First run requires Google account login (OAuth browser flow)
- Auth is cached at `C:\Users\valte\.gemini/`
- If auth expires, agy will prompt for re-login

## Notes

- agy is a Google product — uses Google's Gemini models (free tier available)
- Has its own tool sandbox — file operations, shell commands, code execution
- Does NOT have access to Hermes tools (browser, messaging, etc.)
- For Hermes-native tasks, use Hermes tools directly

## Windows HTTP Server Hosting

`python -m http.server` does NOT stay alive via `terminal(background=true)` on Windows.
Workaround: create a `serve.py` wrapper with `threading.Thread(daemon=True)` + `time.sleep(999)`,
then launch via `cmd /c "start /MIN pythonw serve.py"`.
Always verify with `curl -s http://127.0.0.1:PORT/file.html`.
Use `127.0.0.1` not `localhost`. Add `?v=2` cache-bust if browser shows stale content.

##delegate_task Model Routing

`delegate_task(model="minimax/minimax-m2.5:free")` does NOT route through OpenRouter.
The model param resolves to MiniMax's direct API instead. To use OpenRouter models
via delegate_task, set `delegation.provider=openrouter` and `delegation.model=<model>` 
in config.yaml and omit the model override in the delegate call itself.
