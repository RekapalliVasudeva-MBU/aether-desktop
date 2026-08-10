# Aether-style distributable agent app (Hermes-class, OpenRouter)

Build a local AI agent + personal RAG desktop app that behaves like Hermes:
Normal mode (general agent: tools + skills + memory + MCP) and RAG mode
(grounded on the user's PDF knowledge base), both via OpenRouter.

## Module layout (verified working this session)
```
aether/
  aether/__init__.py
  aether/config.py      # AETHER_HOME, load/save yaml, get_api_key, SOUL/USER.md
  aether/provider.py    # OpenRouter client + chat() w/ tools param
  aether/tools.py       # registry: terminal/read_file/write_file/list_files/web_search
  aether/memory.py      # JSONL durable facts
  aether/skills.py      # discover/load/create + copy_user_skills
  aether/mcp.py         # stdio + http JSON-RPC MCP client
  aether/agent.py       # run_agent() tool-calling loop + get_external_tool_schemas()
  aether/rag.py         # ChromaDB hybrid retrieval (dense+BM25+RRF+rerank)
  aether/telegram.py    # single Telegram bot
  aether_cli.py         # aether chat / doctor / doctor --fix / skills
  desktop_app.py          # FastAPI + pywebview (Normal|RAG toggle, SSE chat)
deploy/                  # self-contained cloud bundle (see openrouter_cloud_deploy.md)
```

## PITFALL #1 — dead tool loop (the big one)
The agent loop MUST pass tool schemas to the model on every call. If you build
`schemas = tool_schemas()` and then call `provider.chat(messages)` WITHOUT
`tools=schemas`, the model never emits `tool_calls` and the loop is a
no-op (it just chats with itself).
FIX pattern:
```python
# provider.py
def chat(messages, model=None, stream=False, tools=None, tool_choice=None):
    kwargs = dict(model=model, messages=messages, temperature=temp, max_tokens=...)
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice or "auto"
    return client.chat.completions.create(**kwargs)

# agent.py
def get_external_tool_schemas():
    schemas = tool_schemas()                       # built-in tools
    for name, client in mcp_mod.connect_all().items():   # merge MCP tools
        for t in client.capabilities:
            schemas.append({"name": f"mcp__{name}__{t['name']}",
                           "description": ..., "parameters": t.get("inputSchema", {...})})
    return schemas

def run_agent(user_message, mode="normal", ...):
    schemas = get_external_tool_schemas()
    ...
    resp = provider.chat(messages, model=model, stream=False, tools=schemas)  # <-- pass it
    msg = resp.choices[0].message
    for tc in (msg.tool_calls or []):
        if fn.name.startswith("mcp__"):      # route MCP vs built-in
            srv, tname = fn.name.split("__", 2)[1:]
            result = mcp_clients[srv].call(tname, args)
        else:
            result = call_tool(fn.name, args)
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
```

## PITFALL #2 — API-key leak in distributable code (BLOCKER-class)
A downloadable agent app MUST NOT read the developer's personal key or hardcode
their username. The bug we shipped + fixed: `get_api_key()` scanned a
hardcoded `C:\Users\valte\AppData\Local\hermes\.env` and `skills.copy_user_skills()`
hardcoded `C:\Users\valte\...` paths. Anyone who downloaded the app would pull
the dev's real OpenRouter key out of the dev's machine path.
CORRECT pattern:
```python
# config.py — key resolves ONLY from env or the agent's OWN .env
def get_api_key():
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key: return key
    own_env = AETHER_HOME / ".env"          # agent's OWN secret file
    if own_env.exists():
        for line in own_env.read_text().splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=",1)[1].strip().strip('"').strip("'")
    return ""
# doctor --fix writes to AETHER_HOME/.env, NEVER a sibling app's file
```
- Remove ALL `valte`/username literals; use `os.environ` / `AETHER_HOME`.
- Verify: `grep -rn "valte\|hermes .env\|hermes\.env" aether/` -> must be CLEAN.
- For the dev's own machine only, seed `<AETHER_HOME>/.env` once out-of-band
  from their personal key so it works without leaking in source.
- Downloaders set THEIR OWN `OPENROUTER_API_KEY` (env or `doctor --fix`).

## PITFALL #3 — OpenRouter/OpenAI requires the `{"type":"function","function":{...}}` wrapper
If you send tool schemas as bare `{"name":..., "description":..., "parameters":...}`,
OpenRouter rejects the request with `400 missing field 'type'` (at
`body.tools[0].function`) — the model never gets to call anything. EVERY schema
you pass to `provider.chat(tools=...)` MUST be wrapped:
```python
def get_external_tool_schemas():
    schemas = []
    for s in tool_schemas():                       # s is a bare schema dict
        if isinstance(s, dict) and s.get("type") == "function":
            schemas.append(s)                        # already wrapped
        else:
            schemas.append({"type": "function", "function": s})
    # MCP tools (already bare dicts) -> wrap the same way
    for name, client in mcp_mod.connect_all().items():
        for t in client.capabilities:
            inner = {"name": f"mcp__{name}__{t['name']}",
                     "description": t.get("description", ""),
                     "parameters": t.get("inputSchema", {"type":"object","properties":{}})}
            schemas.append({"type": "function", "function": inner})
    return schemas
```
Symptom we hit: the chat returned `[error] Error code: 400 ... missing field type`.
Fixing only this unblocked all tool calls.

## PITFALL #4 — schema-enable filter crashes on wrapped schemas (`KeyError: 'name'`)
Once schemas are wrapped (PITFALL #3), any code that does `s["name"]` to read the
tool name now raises `KeyError: 'name'` because the dict is `{"type":"function",
"function":{...}}`. This fires inside the per-item enable filter and kills the
whole chat request. Unwrap correctly in BOTH places that read the name:
```python
def _schema_name(s):
    if isinstance(s, dict) and "function" in s:
        return s["function"].get("name")
    return s.get("name") if isinstance(s, dict) else None
# enable filter:
schemas = [s for s in schemas if enabled.get(_schema_name(s), True)]
# mcp capability filter:
schemas = [s for s in schemas if not _schema_name(s).startswith("mcp__")]
```
Same unwrap needed in `agent.run_agent()` (`s["function"]["name"] if "function" in s
else s.get("name")`).

## PITFALL #5 — "the app can't modify its own config" = no self-config tools
If the in-app agent says "I can't modify my config / install MCP myself", the root
cause is almost always: the tool registry has only generic tools (terminal,
read_file, ...) and NOTHING that writes to the app's own config.yaml. The model has
no tool to call, so it falls back to the refusal. Fix: expose first-class tools that
wrap the existing backend functions, e.g. for MCP:
```python
def _mcp_add_server(args):
    from . import mcp as mcp_mod
    name = (args.get("name") or "").strip()
    spec = args.get("spec") or {}
    if not name or not isinstance(spec, dict):
        return json.dumps({"ok": False, "error": "name and spec are required"})
    mcp_mod.add_server(name, spec)          # writes config.yaml
    return json.dumps({"ok": True, "name": name})
register("mcp_add_server", {schema with "USE THIS when the user asks to add/install an MCP server (e.g. Playwright)"}, _mcp_add_server)
# also mcp_list_servers / mcp_remove_server / mcp_test_server
```
AND tell the model in the system prompt it CAN self-manage that area, e.g.
"You can manage your own MCP servers using the mcp_* tools — when the user asks you
to add an MCP server such as Playwright, call mcp_add_server ... You do NOT need the
user to edit any config file by hand." Then the app literally gets "add the playwright
mcp to your configuration" and the agent writes it to config.yaml + tests the connection.

## PITFALL #6 — providers return tool args as a JSON STRING, not an object
Some OpenAI/OpenRouter SDK versions deliver `tool_call.function.arguments` as a JSON
*string* (e.g. `'{"name":"playwright","spec":{...}}'`) rather than a dict. If your
handler does `args.get("name")` on a str it crashes. Coerce in `call_tool`:
```python
def call_tool(name, args):
    if name not in TOOLS: return json.dumps({"error": f"unknown tool: {name}"})
    if isinstance(args, str):                       # normalize JSON-string args
        try: args = json.loads(args)
        except Exception: args = {}
    if not isinstance(args, dict): args = {}
    return TOOLS[name]["handler"](args)
```
(Also guard the `json.loads(fn.arguments or "{}")` call in the loop itself — if
`fn.arguments` is already a dict, `json.loads(dict)` raises TypeError; check
`isinstance` first.)

## VERIFY the agent actually uses tools (don't trust imports)
An import-success or "schemas=[terminal,...]" print is NOT proof. Run a task
that REQUIRES tool use and assert the disk side effect:
```python
import sys; sys.path.insert(0, ".")
import os, shutil
from aether import agent
proj = r"C:/Users/valte/aether/cal_project"
if os.path.exists(proj): shutil.rmtree(proj)
q = ("Build a small calculator app. Use the terminal tool to create cal_project/, "
       "write calculator.py with add/sub/mul/div (div guards zero), then RUN it via "
       "terminal to verify (print add(2,3)). Store in cal_project/. Do the real work "
       "with tools, don't just describe it.")
print(agent.run_agent(q, mode="normal")[:400])
assert os.path.exists(proj), "agent did NOT use tools"
for r,d,f in os.walk(proj):
    for x in f: print("   ", os.path.join(r,x))
```
This session the agent: created `cal_project/`, wrote a correct `calculator.py`,
RAN it (`add(2,3)=5`, `sub(10,4)=6`, `mul(6,7)=42`, `div(20,5)=4.0`),
and stored it. One test proves tools + skills-preload + terminal control +
file write + real project storage all work.

## Desktop app (Normal | RAG toggle)
- FastAPI `desktop_app.py`: `/ui/` static, `POST /api/chat` SSE streaming
  (mode in body; RAG mode calls `rag.retrieve(q)` and injects context),
  `/api/sessions` list, `/api/sessions/new`, `/api/sessions/<id>`.
- pywebview window loads `http://127.0.0.1:8732/ui/`. SERVER MUST start in a
  daemon thread BEFORE `webview.create_window`/`webview.start()` (see
  pywebview_desktop_app.md for the exact thread pattern). `webview.start()` stays
  on the main thread.
- UI: top toggle Normal|RAG; SSE appends tokens to a bubble; disable send
  while streaming (double-submit guard).
- Headless test env can't render the window — verify via curl on `/ui/`, `/api/chat`,
  `/api/sessions` + read the written file. Tell the user to launch `python
  desktop_app.py` on their laptop to see the window.
