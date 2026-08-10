# Windows Hermes Update Procedure

## Version Numbering

Hermes uses **two version schemes** interchangeably:
- **Semver display:** `v0.14.0`, `v0.15.1` (shown in `hermes --version`)
- **Git tags:** `v2026.5.16`, `v2026.5.29` (date-based, used in the repo)

Mapping (as of May 2026):
| Semver | Git tag | Release date |
|--------|---------|--------------|
| v0.14.0 | v2026.5.16 | May 16 |
| v0.15.1 | v2026.5.29 | May 29 |

## Update Steps (Windows)

Do **not** stop the gateway before updating. The old `hermes update` command can crash on Windows due to file locks on `hermes.exe` / `.pyd` files.

```bash
# 1. Check current version
hermes --version

# 2. Go to the source directory
cd C:\Users\<user>\AppData\Local\hermes\hermes-agent

# 3. Stash local changes (prevents checkout errors)
git stash

# 4. Fetch latest tags
git fetch origin

# 5. Checkout latest release tag
git checkout v2026.5.29   # replace with latest tag

# 6. Reinstall (works over running gateway — do NOT stop first)
uv pip install -e . --force-reinstall --no-cache

# 7. Verify
hermes --version

# 8. Restart gateway to load new version
hermes gateway restart

# 9. Verify gateway is back
hermes gateway status
```

## Common Errors

### `error: Your local changes to be overwritten by checkout`
Run `git stash` first, then retry `git checkout`.

### `hermes update` crashes / hangs
Use the manual git checkout method above. The built-in updater can deadlock on Windows file locks.

### Dashboard buttons unresponsive after update
Log out and log back in, or hard-refresh the dashboard page.

## Cron Jobs After Update
After any Hermes update, verify cron jobs are still scheduled:
hermes cron list
Jobs missed during the gateway restart window won't auto-run. Trigger manually with hermes cron run <job_id> if needed.
