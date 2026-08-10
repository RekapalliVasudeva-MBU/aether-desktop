# Aether agent app — `web_search` tool (DuckDuckGo) pitfall + fix

The built-in `web_search` tool in `aether/tools.py` queries DuckDuckGo. This is the
tool the agent uses whenever the user says "search the web", "look it up online",
"find current info", or "add a search capability". It MUST return real results or
the agent appears to "not understand" the user (the exact bug reported in the
v1.2.5->v1.2.7 cycle).

## Root cause of the broken search
The original implementation hit `https://html.duckduckgo.com/html/?q=<query>` (GET
with a query string). DuckDuckGo now serves a JS/challenge wall on that GET URL, so
the returned HTML has NO `result__a` links -> the regex finds nothing -> the tool
returns `{"results": []}` -> the agent "can't search".

## The fix (verified working, v1.2.7)
Use a **POST form** to the same HTML endpoint, with ONLY `--data-urlencode q=`.
A real form POST returns parseable results (10+ links).

```python
import re, subprocess, json
def _web_search(args):
    q = args.get("query", "")
    if not q:
        return json.dumps({"error": "query is required"})
    if not shutil.which("curl"):
        return json.dumps({"error": "curl not available for web search"})
    try:
        out = subprocess.run(
            ["curl", "-s",
             "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
             "--data-urlencode", f"q={q}",          # <-- POST form, ONLY this field
             "https://html.duckduckgo.com/html/"],
            capture_output=True, text=True, timeout=25,
        ).stdout
        links = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', out, re.S)
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', out, re.S)
        clean = lambda s: re.sub(r"<[^>]+>", "", s).strip()
        results = [{"title": clean(t), "url": h,
                    "snippet": clean(snippets[i]) if i < len(snippets) else ""}
                   for i, (h, t) in enumerate(links[:5])]
        return json.dumps({"query": q, "results": results, "count": len(results)})
    except Exception as e:
        return json.dumps({"error": f"web search failed: {e}"})
```

## Pitfalls (learned the hard way)
- **DO NOT add `--data b=` or `--data kl=us-en`** — extra POST fields make DDG return
  an EMPTY result set (0 links). Use ONLY `--data-urlencode q=`.
- The snippet class is `result__snippet` (lowercase `s`), NOT `result-snippet` and
  NOT `class="result__snippet"` inside a `<td>`. Match `class="result__snippet"[^>]*>(.*?)</a>`.
- `lite.duckduckgo.com/lite/` was tested as an alternative but is ALSO intermittently
  walled/rate-limited from some IPs — the `html/` POST form is the reliable one.
- The DuckDuckGo Instant Answer API (`api.duckduckgo.com/?q=...&format=json`) returns
  empty `Results` for most queries (only `Abstract` for a few) — NOT a substitute for
  real web search.

## "Add the DuckDuckGo MCP" user request
There is **no official DuckDuckGo MCP server package** (not on npm, not in the MCP
registry). When the user asks to "add duckduckgo mcp" or "add a search MCP", the
agent should NOT loop trying `mcp_add_server` with guessed package names (they all
fail with "file not found" / "no such server"). Instead: tell the user that
`web_search` IS the DuckDuckGo-backed search, and use it directly. The `web_search`
tool description should say: "USE THIS whenever the user asks you to search the web,
look something up online, find current info, or 'add a search capability'."

## Verify the fix
Standalone (fast, no rebuild needed):
```bash
cd /c/Users/valte/aether && python -c "
import sys; sys.path.insert(0,'.')
from aether.tools import TOOLS
import json
d = json.loads(TOOLS['web_search']['handler']({'query':'openrouter free models 2026'}))
print('count:', d.get('count'))
for x in d.get('results',[])[:3]: print('-', x['title'][:55], '|', x['url'][:45])
"
```
Expect `count: 5` with real OpenRouter result titles.

End-to-end (through the agent, after rebuild): POST `/api/chat` with a message that
asks to search and report the first result title; the streamed `token` should contain
a real DuckDuckGo result title (e.g. "Free AI Models on OpenRouter").
