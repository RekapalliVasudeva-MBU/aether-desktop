# Cron Job Failure Diagnosis

Class-level reference for diagnosing Hermes cron job failures on Windows.

## Symptom

Cron job shows `last_status: error` in `cronjob(action="list")` output, or the daily/weekly digest didn't arrive.

## Diagnosis Workflow

### 1. Check the Error Transcript

Cron jobs write output to `~/.hermes/cron/output/<job_id>/<timestamp>.md`. The most recent file contains the error:

```bash
# On Windows, HERMES_HOME may differ from ~/.hermes — check both:
ls "$HERMES_HOME/cron/output/<job_id>/" 2>/dev/null
ls ~/.hermes/cron/output/<job_id>/ 2>/dev/null

# Read the latest output (smallest file is usually the failed run)
cat <output-file>.md
```

The output file contains:
- The full prompt that was sent
- The error traceback under `## Error`

### 2. Common Error Patterns

#### `RuntimeError: HTTP 400: invalid params, unknown model '<model-name>'`

**Meaning:** The cron job tried to use a model that doesn't exist or isn't available on the provider.

**Root cause chain:**
1. Primary model (e.g., `openrouter/owl-alpha`) had a transient failure
2. System fell back to a secondary model configured in `delegation.model` or `fallback_providers`
3. That model name is invalid/expired (e.g., `minimax-m2.5:free` was removed from OpenRouter)

**Fix:** Update `config.yaml` to replace the broken model:
- `delegation.model` — used for subagent/delegation work
- `fallback_providers[].model` — used when primary model fails

Use `hermes config set delegation.model "openrouter/<working-model>"` or edit via Python yaml (config.yaml is protected from `patch`).

#### `RuntimeError: <provider> API key not configured`

**Meaning:** The fallback provider needs an API key that isn't set.

**Fix:** Either add the key to `.env` or remove that fallback from config.

#### Timeout / No Output File

**Meaning:** The job was killed by the 3-minute hard interrupt (runaway loop) or never started.

**Fix:** Check if the prompt is too complex. Simplify or split into smaller steps.

### 3. Verify the Fix

After fixing the config, trigger a manual run:
```
cronjob(action="run", job_id="<job-id>")
```

Wait for completion and check `last_status` changes to `ok`.

### 4. Prevention

- **Use reliable free models** for cron jobs (they run unattended — paid models cost money)
- **Test the model** before assigning it to a cron job: `hermes chat "test" --model <model-name>`
- **Check `fallback_providers`** list — remove any model you haven't verified recently
- **Monitor `delegation.model`** — this is often overlooked when updating the primary model

## Windows-Specific Notes

- Cron output path on Windows: `C:\Users\<user>\AppData\Local\hermes\cron\output\<job_id>\`
- `HERMES_HOME` env var may point to `~/.hermes` while actual data lives in `AppData/Local/hermes` — always check both locations
- The cron scheduler runs inside the Hermes gateway process — restart the gateway after config changes: `hermes gateway restart`
