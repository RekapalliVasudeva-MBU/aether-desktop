---
name: hermes-cron-troubleshooting
description: Diagnose and fix failing Hermes cron jobs — read job output, interpret agent-loop errors, and repoint dead/flaky models.
version: "1.0"
author: Hermes Agent
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [cron, scheduled-jobs, openrouter, debugging]
    category: devops
---

# Hermes Cron Job Troubleshooting

Recurring operational task: a scheduled cron job silently produces errors or empty output. Diagnose from the output files and fix it permanently.

## When to Use

- User reports "the cron job isn't working" / "still didn't fix it"
- A digest/newsletter/scheduled task arrives empty, truncated, or with an error block
- `last_status: error` in `cronjob action=list`

## Step 1: Locate the job + its output

```bash
# List jobs, find the failing job_id
# (cronjob action=list)

# Output files live here — one .md per run:
#   <HERMES_HOME>/cron/output/<job_id>/YYYY-MM-DD_HH-MM-SS.md
ls -t "<HERMES_HOME>/cron/output/<job_id>/" | head -3
```

`HERMES_HOME` is usually `C:\Users\<user>\AppData\Local\hermes` on Windows (NOT `~/.hermes`). Profile-aware: use `get_hermes_home()`.

## Step 2: Read the last few output .md files

Each run file ends with either `## Response` (success) or `## Error` (failure). The error text is the diagnosis:

| Error in output | Root cause | Fix |
|---|---|---|
| `'NoneType' object is not subscriptable` | Model returned malformed/empty response; agent loop burned all 90 iterations failing to parse. **Classic symptom of a `:free` OpenRouter model** (rate-limited / flaky for multi-tool tasks). | Repoint the job to a reliable (non-`:free`) model. See Step 3. |
| `RuntimeError: Failed to initialize OpenAI client: No module named 'X'` | Transient env/pydantic version issue. | Usually resolves on next run once env is healthy; verify with a manual `cronjob action=run`. |
| `[SILENT]` delivered but no content | Working as designed — nothing new to report. Not a bug. | None. |

## Step 3: Repoint the model (most common real fix)

`:free` OpenRouter models are the #1 cause of cron failures. Switch the job to a stable model:

```
cronjob action=update job_id=<id> model={"model":"<provider>/<model>","provider":"<provider>"}
```

- Use the user's actual configured default (check `config.yaml` → `model.default`), NOT a guessed/removed model.
- **Verify the model still exists** before pinning — OpenRouter retires models (e.g. `openrouter/owl-alpha` was removed; pinning it produces more failures). If unsure, ask the user or pick their current `model.default`.
- After updating, run the job once manually to confirm it produces a real digest:
  ```
  cronjob action=run job_id=<id>
  ```
  Then read the newest output `.md` — success = a `## Response` with real content, not an error block.

## Step 4: Update memory if a model was retired

If you discover a model in the user's config/memory is dead on the provider, update memory so future sessions don't repoint to it. (e.g. "openrouter/owl-alpha was removed — do not use.")

## Hard rules

- **Always verify with a real run**, not just a config change. The user has already been burned by "fixed" jobs that weren't. A manual `cronjob action=run` + reading the output file is the proof.
- Don't guess model names — read `config.yaml` `model.default` or ask.
- Cron jobs run headless with their own env; an unset key in *your* shell doesn't mean the job lacks one.

## Pitfalls

- Editing `jobs.json` by hand is unnecessary — `cronjob action=update` is the supported path.
- A single transient error (pydantic/import) often self-heals; don't over-rotate the model for it. The `NoneType not subscriptable` + burned-iterations pattern is the reliable "flaky free model" signal.
- The `deliver` target (telegram/origin/etc.) is separate from the model — fixing the model doesn't change delivery.
