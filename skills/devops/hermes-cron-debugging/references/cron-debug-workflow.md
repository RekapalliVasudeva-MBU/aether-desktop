# Cron Debug Workflow — Reference

## Path layout (profile-aware)
- Config: `<HERMES_HOME>/cron/jobs.json` (array of jobs; each has `model`, `provider`, `schedule`, `deliver`, `enabled_toolsets`)
- Output logs: `<HERMES_HOME>/cron/output/<job_id>/<YYYY-MM-DD_HH-MM-SS>.md`
- On this machine: `HERMES_HOME = C:\Users\valte\AppData\Local\hermes`
  (NOT `~/.hermes` — this profile uses AppData)

## Copy-paste sequence
```bash
# 0. Find jobs + IDs
cronjob action=list

# 1. List output files for a failing job (newest first)
ls -t /c/Users/valte/AppData/Local/hermes/cron/output/<job_id>/

# 2. Read the newest .md to get the root-cause error string
#    ~1.4KB file ending in "## Response" with an error = FAILURE
#    ~8KB file with real digest = SUCCESS

# 3. Repoint model (example: to agent's active model)
cronjob action=update job_id=<id> model={"model": "tencent/hy3:free", "provider": "openrouter"}

# 4. VERIFY — run it for real, then re-read newest output .md
cronjob action=run job_id=<id>
```

## Error-string → meaning (seen this session)
- `Error: 'NoneType' object is not subscriptable` + "maximum iterations (90) but couldn't summarize"
  → Pinned `:free` model (nvidia/nemotron-3-super-120b-a12b:free) returned empty/garformed response; agent loop subscripted None.
- `RuntimeError: Failed to initialize OpenAI client: No module named 'pydantic.fields'`
  → Transient env/dependency mismatch in cron runner; re-run to confirm it clears (pydantic 2.13.4 present on host).

## Models to AVOID pinning on cron (multi-tool jobs)
- Any OpenRouter `:free` model — rate-limits choke the tool loop.
- Removed-from-catalog models — e.g. `openrouter/owl-alpha` (deleted from OpenRouter; do not use).

## What worked
Daily AI News Digest (43dde6b90d3d) and Weekly RAG News Digest (989893963ab1) both repointed from
`nvidia/nemotron-3-super-120b-a12b:free` → `tencent/hy3:free`. Manual `cronjob action=run` produced a full
86-line 10-item digest and delivered to Telegram. root cause = free-tier model, not the cron engine.
