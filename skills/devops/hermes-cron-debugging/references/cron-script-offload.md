# Offloading deterministic work into a cron `script` (free-model-only fix)

When a cron job "succeeds" (last_status ok) but delivers wrong-language, off-track,
or false-[SILENT] content under the user's **free-models-only** policy, the fix is to
reduce the LLM's burden: do the brittle fetch/parse in a tested Python `script`, and
let the prompt only summarize the script's stdout.

## Why
Free OpenRouter `:free` models handle light summarization fine but derail on
multi-step terminal-fetch-parse loops, especially when a source returns empty and the
model fills the gap with process logs or switches language. Removing the fetch/parse
from the loop removes the derailment trigger.

## How
1. Write a script to `<HERMES_HOME>/scripts/` (this machine:
   `C:\Users\valte\AppData\Local\hermes\scripts\`). It must print the already-extracted
   data to stdout (the cron engine injects stdout into the prompt as context).
2. Attach it: `cronjob action=update job_id=<id> script="my_fetch.py"`
   - The `script` value MUST be a **bare filename** in the scripts dir. An absolute
     `C:\...` or `~/...` path is rejected: "Script path must be relative to ~/.hermes/scripts/".
   - With a script set, `no_agent` is false by default: the LLM still runs and receives
     stdout as context — design the prompt to REWRITE stdout, not re-fetch.
3. Harden the prompt:
   - "Write ONLY in English. NEVER use any other language."
   - "Output ONLY the final digest — no process logs, status tables, or self-analysis."
   - "If stdout is empty, respond exactly [SILENT]. Otherwise produce the digest from stdout."
   - "Never return [SILENT] unless stdout is truly empty."

## Verified recipe — Daily AI News fetch (job 43dde6b90d3d)
Sources that WORK with a `Mozilla/5.0` User-Agent and plain fetch:
- HN Algolia (AI-filtered, JSON, bot-friendly, real recency signal):
  `https://hn.algolia.com/api/v1/search_by_date?query=AI&tags=story&hitsPerPage=50`
  Iterate `hits`, keep `title` + (`url` or `item?id=<objectID>`), filter by
  `NOW - created_at_i <= 3*24*3600` for last-3-days recency.
- The Verge AI section (works with UA header):
  `https://www.theverge.com/ai-artificial-intelligence`
  Regex `<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>`, keep links with `/\d{4}/` or
  `/ai-artificial-intelligence`, prefix `https://www.theverge.com` if href starts `/`.

Sources that FAIL with plain curl (return 0 bytes) — avoid:
- `https://news.ycombinator.com/` (front page HTML) — blocks curl.
- `https://arstechnica.com/ai/` — blocks curl.

Keyword filter to keep only AI/ML items: regex over
`ai|llm|gpt|claude|gemini|llama|mistral|openai|anthropic|xai|grok|rag|agent|model|
neural|diffusion|transformer|machine learning|deep learning|inference|fine-?tun|
embedding|pytorch|tensorflow|mlops|copilot|chatbot|multimodal` (case-insensitive).

Known-good file: `C:\Users\valte\AppData\Local\hermes\scripts\daily_ai_news_fetch.py`
(prints "N. TITLE | URL", up to 10, AI-filtered, last 3 days).

## Test the script before attaching
Run it standalone to confirm it emits real recent items:
`python3 ~/AppData/Local/hermes/scripts/daily_ai_news_fetch.py`
If it prints general non-AI front-page junk, the source/query/filter is wrong — fix
before wiring it into the job.
