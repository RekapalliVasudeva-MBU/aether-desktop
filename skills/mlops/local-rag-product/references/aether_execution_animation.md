# Aether — execution-step animation + context compaction

Two patterns the user explicitly demanded ("see the agent think/work/use tools,
not a blank wait" + "make it optimized/intelligent like the Claude Code leak PDF +
Hermes"). Both verified in v1.2.8.

## 1. SSE execution-step timeline (live agent animation)

The chat UI must show a visible, animated timeline of the agent working:
🧠 Thinking → 🔧 tool_name(args) → result → ✍️ answer. A final-only answer with
no working steps reads to this user as "the app can't do basic tasks".

### Backend: emit `step` events from the `/api/chat` SSE loop

In `desktop_app.py` `api_chat`, define a local `emit(obj)` and yield step events
BEFORE/AROUND the model + tool calls. The agent loop lives inline in `api_chat`
(it does NOT call `agent.run_agent` — see the DEAD-TOOL-LOOP / must-call-run_agent
pitfalls in `aether_agent_app.md`). Stream shape:

```python
def emit(obj): return f"data: {json.dumps(obj)}\n\n"

# before the first model call
yield emit({"step": "thinking", "label": "Thinking…", "session_id": sid})
resp = provider.chat(buf, model=body.get("model"), stream=False,
                     tools=schemas, reasoning_effort=reasoning)
msg = resp.choices[0].message
content = msg.content or ""
tool_calls = getattr(msg, "tool_calls", None)
if not tool_calls:
    yield emit({"step": "answer", "label": "Composing answer", "session_id": sid})
    yield emit({"token": content, "session_id": sid, "citations": citations})
    # ...save session...
    yield emit({"done": True, "session_id": sid}); return
# tool-calling loop: surface each planned call, then its result
full = content
loop_msgs = list(buf) + [{"role":"assistant","content":content,
    "tool_calls":[{"id":tc.id,"type":"function","function":{"name":tc.function.name,
    "arguments":tc.function.arguments}} for tc in tool_calls]}]
turn = 0
while turn < 12:
    turn += 1
    for tc in (loop_msgs[-1].get("tool_calls") or []):
        fn = tc["function"]
        try: a = json.loads(fn.get("arguments") or "{}")
        except Exception: a = {}
        preview = json.dumps(a, ensure_ascii=False)
        if len(preview) > 200: preview = preview[:200] + "…"
        yield emit({"step":"tool_start","tool":fn["name"],"args":preview,
                    "turn":turn,"session_id":sid})
    r2 = provider.chat(compression.trim_history(loop_msgs), stream=False,
                       tools=_enabled_schemas(), reasoning_effort=reasoning)
    m2 = r2.choices[0].message
    full += (m2.content or "")
    if not getattr(m2, "tool_calls", None): break
    loop_msgs.append({"role":"assistant","content":m2.content or "",
        "tool_calls":[{"id":tc.id,"type":"function","function":{"name":tc.function.name,
        "arguments":tc.function.arguments}} for tc in m2.tool_calls]})
    for tc in m2.tool_calls:
        fn = tc.function
        try: args = json.loads(fn.arguments or "{}")
        except Exception: args = {}
        result = tools_mod.call_tool(fn.name, args)
        step_result = result[:600] + "…" if isinstance(result,str) and len(result)>600 else result
        yield emit({"step":"tool_end","tool":fn.name,"result":str(step_result),
                    "turn":turn,"session_id":sid})
        loop_msgs.append({"role":"tool","tool_call_id":tc.id,"content":result})
yield emit({"token": full, "session_id": sid, "citations": citations})
# ...save session, then:
yield emit({"done": True, "session_id": sid})
```

Step event types: `thinking`, `answer`, `tool_start` (has `tool`,`args`,`turn`),
`tool_end` (has `tool`,`result`,`turn`). The UI renders them as a timeline.

### Frontend: render steps in `index.html` `send()`

Parse `step` events; build a `.steps` container inside the AI message bubble.
Every dynamic value MUST pass through `esc()` (HTML-escape) before interpolation —
the values are server-derived (tool names/args/results), not user HTML, but escape
defensively. Animation: a blinking `▌` (`@keyframes blink`) on in-progress steps,
`.done` class turns the left border green when finished.

```js
const steps = document.createElement('div'); steps.className='steps'; ai.appendChild(steps);
const body = document.createElement('div'); body.className='answer-body'; ai.appendChild(body);
function stepEl(kind, html){ const d=document.createElement('div'); d.className='step step-'+kind;
  d.innerHTML=html; steps.appendChild(d); m.scrollTop=m.scrollHeight; return d; }
function spin(){ return '<span class="spin">▌</span>'; }
// in the SSE read loop:
if(j.step==='thinking'){ thinkingEl=stepEl('thinking','<span class="ic">🧠</span><span>'+esc(j.label||'Thinking…')+'</span>'+spin()); }
else if(j.step==='answer'){ if(thinkingEl) thinkingEl.classList.add('done'); thinkingEl=null;
  stepEl('answer','<span class="ic">✍️</span><span>'+esc(j.label||'Composing answer')+'</span>'); }
else if(j.step==='tool_start'){ if(thinkingEl){thinkingEl.classList.add('done');thinkingEl=null;}
  curTool=stepEl('tool','<span class="ic">🔧</span><span class="tt">'+esc(j.tool)+'</span><span class="ta">'+esc(j.args||'')+'</span>'+spin()); }
else if(j.step==='tool_end'){ if(curTool){curTool.classList.add('done');
  const r=document.createElement('span'); r.className='tr'; r.textContent=(j.result||'').slice(0,300);
  curTool.appendChild(r); curTool=null;} }
else if(j.token){ body.textContent += j.token; if(ai._cites===undefined && j.citations) ai._cites=j.citations; }
```

CSS (add near `.msg` rules):
```css
.steps{width:100%;margin:6px 0;display:flex;flex-direction:column;gap:4px;}
.step{display:flex;align-items:center;gap:7px;font-size:12px;color:var(--muted);
  padding:5px 9px;border-radius:7px;background:var(--panel2);border-left:2px solid var(--border);
  animation:stepin .25s ease;}
@keyframes stepin{from{opacity:0;transform:translateY(4px);}to{opacity:1;transform:none;}}
.step .tt{color:var(--accent2);font-weight:600;}
.step .ta{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px;opacity:.85;
  max-width:55%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.step .tr{font-size:11px;opacity:.7;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:block;}
.step.done{border-left-color:var(--ok);color:var(--text);}
.step.done .spin{display:none;}
.spin{display:inline-block;animation:blink 1s steps(2,start) infinite;color:var(--accent);}
@keyframes blink{50%{opacity:0;}}
```

### Verify
Launch headless (`AETHER_HEADLESS=1 ./Aether.exe`), POST `/api/chat` with a
web-search query, and confirm the raw stream contains `{"step":"thinking"...}`,
`{"step":"tool_start","tool":"web_search"...}`, and a `token`. The UI shows the
timeline without code changes if the events are present.

## 2. Two-layer context compaction (fixes "9000 files" blow-up)

Source insight: the Claude Code leak analysis describes two-layer compaction
(rule-based Snip + preserve_last_n) + a 32KB tool-output cap to stop context
bloat. The old `compression.trim_history` truncated tool results at 4KB and dropped
tool context from old turns — too aggressive and lost needed results.

`aether/compression.py` (verified: 81 msgs -> 26; tool output capped at ~24KB):

```python
KEEP_TURNS = 12            # recent (user,assistant) pairs kept verbatim
TOOL_RESULT_MAX = 24000    # 32KB Snip cap on any single tool result
MAX_PROMPT_CHARS = 120_000 # hard ceiling; drop oldest tool/assistant blocks first

def _trim_tool(m):        # Layer 1 cap
    c = m.get("content","")
    if isinstance(c,str) and len(c) > TOOL_RESULT_MAX:
        return {**m, "content": c[:TOOL_RESULT_MAX] + "\n…[result truncated for token savings]"}
    return m

def _recap(dropped):      # rule-based Snip recap (layer 2)
    topics=[m["content"][:70] for m in dropped if m.get("role")=="user" and isinstance(m.get("content"),str)]
    n=sum(1 for m in dropped if m.get("role")=="tool")
    bits=[]
    if topics: bits.append("user asked: "+"; ".join(topics))
    if n: bits.append(f"{n} tool result(s) consolidated")
    return "[earlier conversation recap] "+"; ".join(bits) if bits else "[earlier context omitted]"

def trim_history(messages):
    # keep system + recent KEEP_TURNS*2 conversational pairs; recap the rest
    # keep tool results attached to the preserved window; cap each with _trim_tool
    # then _enforce_budget drops oldest tool/assistant blocks if still > MAX_PROMPT_CHARS
    ...
```

Key: when the model would otherwise load thousands of file listings, this caps
each result at 24KB and collapses old turns into a one-line recap — the prompt
stays bounded. Pair with the system-prompt rule (in `agent.build_system_prompt`):
"for big codebases, prefer a single search_files/list call over reading thousands
of files; do not dump 9000 file listings into context."

### System-prompt fusion (PDF + Hermes)
Add to `build_system_prompt` a "Workflow discipline" block:
1. Think first — state plan in 1-2 lines before tools.
2. One tool at a time; targeted search over dumping file listings.
3. After each tool result, reflect briefly, then continue or answer.
4. For many-file tasks, delegate via `delegate_task` (fresh context per sub-agent).
Plus: "there is no official DuckDuckGo MCP server — `web_search` IS the
DuckDuckGo search; use it directly." (see `aether_web_search.md`.)
