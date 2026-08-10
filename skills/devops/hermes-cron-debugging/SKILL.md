---
name: hermes-cron-debugging
description: Diagnose and fix failing Hermes cron jobs — read output logs, identify model-related root causes (esp. free-tier or removed models), repoint to a working model, and verify the run for real.
---

# Debugging Hermes Cron Jobs

## Trigger
User says a cron job "isn't working", "failed", "stopped running", or pastes a cron delivery error such as "I reached the maximum iterations (90) but couldn't summarize" or "Error: 'NoneType' object is not subscriptable".

## Diagnostic steps (in order)
1. `cronjob action=list` — for each job read `model`, `provider`, `last_status`, `last_error`, `last_delivery_error`. The broken job shows `last_status: "error"` or a stale/garbage `last_error`.
2. Locate output logs: `<HERMES_HOME>/cron/output/<job_id>/`. HERMES_HOME is profile-aware — use `get_hermes_home()`; on this machine it is `C:\Users\valte\AppData\Local\hermes`. Files are named `<YYYY-MM-DD_HH-MM-SS>.md`.
3. Read the **newest** output file. Two shapes:
   - ~8KB with a real `## Response` body = success.
   - ~1.4KB ending in `## Response` with an error string, or a `## Error` block = failure. That string is the root cause.
4. Map the error to a cause (see table below), then fix.

## Root-cause patterns
| Symptom in output | Meaning | Fix |
|---|---|---|
| `'NoneType' object is not subscriptable` + "maximum iterations (90)" | Pinned model returned malformed/empty responses (no tool-call). The agent loop subscripted `None` and burned all iterations. | Switch model (see PITFALL). |
| `No module named 'pydantic.fields'` or similar import error | Transient env/dependency mismatch in the cron runner's isolated env. | Usually self-resolves — re-run to confirm. |
| `RuntimeError: Failed to initialize OpenAI client` | Auth/client init issue in the runner env. | Re-run; if it persists, check the provider key reaches the cron runner. |
| `⚠️ Skill(s) not found and skipped: <name>` in output + job wrote NO output file | The job referenced a skill that doesn't exist (e.g. `web-research`) AND/OR had `enabled_toolsets` without `web`, so the agent had no web tools and gave up. **`execution_success` can still be `true`** — the run "succeeded" at producing a surrender message. | Fix the skill/toolset (see PITFALL: silent skill-skip + missing web toolset), re-run, and verify the actual output artifact exists on disk. |

## PITFALL — free-tier models break cron jobs
OpenRouter `:free` models (e.g. `nvidia/nemotron-3-super-120b-a12b:free`) are heavily rate-limited and frequently return empty/malformed responses. For any cron job that uses tools (terminal, web, etc.), a `:free` model will often choke exactly like the `NoneType` error above. **Do not pin cron jobs to `:free` models for multi-tool tasks.**

Also: **do not pin cron jobs to models that may have been removed from the provider catalog.** Example from this session: `openrouter/owl-alpha` was removed from OpenRouter and fails. When unsure, point the job at the agent's *current active model* (the model this session runs on) rather than a hardcoded string.

### FREE-MODEL-ONLY CONSTRAINT — offload work to a `script`, don't change the model
This user's policy is **ONLY free (`:free`) models — never paid** (see `hermes-free-model-policy`). So "switch to a paid model" is NOT an option. The reliable fix under that constraint is NOT model-swapping but **burden reduction**:
- Move brittle deterministic work (web fetch + HTML/XML parse + filtering) OUT of the LLM loop and INTO a `script:` (a tested Python file run before the prompt). The prompt then only does light English summarization of already-extracted data. Free models handle light summarization reliably; they choke on multi-step terminal-fetch-parse loops.
- If a free model keeps derailing a tool-heavy job, the answer is almost always: reduce its tool calls via a `script`, not change models.
See `references/cron-script-offload.md` for the pattern and gotchas (and the `references/` dir for `daily_ai_news_fetch.py` as a known-good news-fetch offload).

## PITFALL — `last_status: ok` + `execution_success: true` does NOT mean the CONTENT is correct
A cron job can "succeed" while delivering **garbage content**. Two real shapes seen this session (Daily AI News Digest, job `43dde6b90d3d`, 2026-07-13 run):
1. **Wrong language / off-track output.** The free model could not fetch sources (Hacker News & Ars Technica blocked plain `curl` → empty files), then instead of the English digest it wrote a Spanish-language "structured checkpoint" of its own failed downloads. `last_status` was still `ok`. The user saw Spanish and said "do it in english."
   - Root cause: sources failed AND the prompt did not hard-lock language/output shape AND the model was free-tier and prone to derailing on thin data.
   - Tell-tale sign: output `.md` contains process logs, status tables, "checkpoint", or non-English text instead of the expected digest body.
2. **False `[SILENT]`.** A later run found "no news" and returned exactly `[SILENT]` — delivering nothing to the user. The free model bailed instead of producing from the one source that did work (The Verge).
   - `[SILENT]` is only correct when stdout is genuinely empty. If any source returned data, the job MUST produce a digest, not silence.

**Fix for both:**
- Harden the prompt: `Write ONLY in English. NEVER use any other language. Output ONLY the final digest — no process logs, status tables, or self-analysis. If a source fails or is empty, silently skip it and use whatever data you DID retrieve. Never return [SILENT] unless ALL sources are empty.`
- Make the fetch robust (see script-offload ref): use bot-friendly endpoints — `https://hnrss.org/frontpage` or better `https://hn.algolia.com/api/v1/search_by_date?query=AI&tags=story&hitsPerPage=50` (filter by `created_at_i` to last 3 days) and `https://www.theverge.com/ai-artificial-intelligence` with a `Mozilla/5.0` User-Agent (plain `curl` to news.ycombinator.com and arstechnica.com returns 0 bytes).
- Verify the actual delivered content is the expected language/shape, not just that `execution_success` is true.

## PITFALL — `execution_success: true` is NOT proof the job did its work
For jobs that are supposed to **write a file or directory**, a run can return `execution_success: true` while producing NOTHING on disk. This happens when:
- the prompt referenced a skill that doesn't exist (silently skipped — look for `⚠️ Skill(s) not found and skipped` in the output `.md`), and/or
- `enabled_toolsets` omitted the tool the job needed (e.g. a research job with only `terminal`+`file`, no `web`).
The agent then "succeeds" at explaining it can't do the task. **Always verify the output artifact exists:**
the run log lives at `<HERMES_HOME>/cron/output/<job_id>/`, but the REAL target (e.g. `C:\Users\valte\project_rag\rag_pdfs\weekly_technique_hunter_<date>.md`) must be confirmed present on disk. If it's missing, the job failed in practice regardless of `execution_success`.

## PITFALL — silent skill-skip + missing `web` toolset on research jobs
- Skill names in the `skills`/`skill` field must be REAL skill names (verify with `skills_list`). This session the job referenced `web-research`, which does not exist; the real one is `research`. A wrong name = silent skip = no research.
- Cron jobs with `enabled_toolsets` set get ONLY those tools. A web-research job MUST include `"web"` in `enabled_toolsets` (plus `terminal`+`file`) or the agent has no `web_search` and gives up. If you omit `enabled_toolsets` entirely, the job gets the default full set — but if you set it, you must enumerate `web`.

## PITFALL — don't confuse an on-demand digest with the cron job's actual output
When the user says "you didn't run the daily job today" or "the digest is wrong", do NOT
reach for a differently-generated file (e.g. an on-demand digest produced in a chat session,
or a sibling `RAG-lecture` digest). Those are separate artifacts and will mislead the
diagnosis. Go straight to the job's own run log at `<HERMES_HOME>/cron/output/<job_id>/`
(read the newest `.md`) and to `cronjob action=list` for `last_status`/`last_run_at`. The
definitive answer about what the cron job actually produced is in THAT folder, not in any
file the agent happened to generate in conversation.
Even when a `:free` model "works" (run succeeds, file written), it may INVENT source URLs, paper IDs, and benchmark numbers (e.g. fake `references/rag-lecture-series.md` paths, "37% improvement"). The output looks clean but cites nothing verifiable. For research/digest jobs, harden the prompt: "Every item MUST include a REAL URL you actually retrieved via web_search. Do NOT invent, guess, or fabricate URLs or numbers. If you cannot verify a real source, omit the item." Re-run and confirm real `arxiv.org`/GitHub URLs appear before trusting the digest.

## Fix
1. Repoint the model to a working one if the user permits non-free. Prefer the agent's active model (this session: `tencent/hy3:free`, provider `openrouter`) unless the user specifies otherwise. **Under the free-only policy, do NOT switch to a paid model — instead offload work to a `script` (see references/cron-script-offload.md).**
2. **Offload deterministic work to a `script` (preferred fix under free-only):** write a tested Python file into the scripts dir and set it on the job via `cronjob action=update job_id=<id> script="daily_ai_news_fetch.py"`. **The `script` value MUST be a bare filename in the scripts dir (on this machine `C:\Users\valte\AppData\Local\hermes\scripts\`), NOT an absolute or `C:\...` path** — an absolute path is rejected with an error about being relative to `~/.hermes/scripts/`. The script's stdout is injected into the prompt as context; design the prompt to rewrite stdout, not re-fetch.
3. **Verify the fix for real — do not just change config:**
   `cronjob action=run job_id=<id>`
   Then re-read the newest output `.md`. It must contain real, correct-language content, not an error block, a process log, or a false `[SILENT]`. A successful manual run is the proof.
4. Confirm the delivery target: for `deliver: telegram` jobs, the run returns `execution_success: true` and the output file has a proper digest.

## Verification checklist
- [ ] `cronjob action=list` shows the job with the updated model (or, under free-only, the `script` set)
- [ ] Manual `cronjob action=run` returns `execution_success: true`
- [ ] Newest output `.md` has real content (NOT `## Error` / `NoneType`)
- [ ] **Content is correct-language and on-shape** — NOT a process log, status table, "checkpoint", non-English text, or a false `[SILENT]` (see the `last_status: ok` PITFALL). Read the actual `## Response` body, don't trust `last_status`.
- [ ] **For file/dir-writing jobs:** the actual output artifact exists on disk (not just the run log). `execution_success: true` alone is insufficient — see PITFALL above.
- [ ] **For research jobs:** output contains REAL fetched URLs (e.g. `arxiv.org`, GitHub), not fabricated ones — see PITFALL above.
- [ ] `next_run_at` is still scheduled (schedule unchanged)

See references/cron-debug-workflow.md for the exact path layout and a copy-paste command sequence, and references/cron-script-offload.md for the free-model-only fix (offload fetch/parse into a `script`).
