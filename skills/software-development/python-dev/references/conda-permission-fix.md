# Conda Permission Fix — Windows System-Wide Install

Full diagnostic flow and fix for `EnvironmentNotWritableError` on Windows.

## Error Transcript

```
$ C:\ProgramData\Anaconda3\Scripts\conda.exe update conda -y --dry-run

3 channel Terms of Service accepted
Retrieving notices: done

EnvironmentNotWritableError: The current user does not have write permissions to the target environment.
  environment location: C:\ProgramData\Anaconda3
```

## Root Cause

Anaconda installed as "All Users" → `C:\ProgramData\Anaconda3\`. This folder is owned by `SYSTEM`/`TrustedInstaller`. Standard users cannot write to it.

## Diagnostic Steps

1. **Confirm install location:**
   ```powershell
   where.exe conda
   # C:\ProgramData\Anaconda3\Scripts\conda.exe → system-wide (problematic)
   # C:\Users\valte\Anaconda3\Scripts\conda.exe → user-level (no issue)
   ```

2. **Check conda info:**
   ```powershell
   & 'C:\ProgramData\Anaconda3\Scripts\conda.exe' info
   # Look for: "base environment : C:\ProgramData\Anaconda3 (read only)"
   ```

3. **Verify user is in admin group:**
   ```powershell
   whoami /groups | findstr "S-1-5-32-544"
   # No output → not admin, cannot use RunAs
   ```

## Fix: PowerShell RunAs

```powershell
# Single command pattern (one at a time — -Wait blocks until done):
Start-Process -FilePath 'C:\ProgramData\Anaconda3\Scripts\conda.exe' -ArgumentList 'update','conda','-y' -Verb RunAs -Wait
Start-Process -FilePath 'C:\ProgramData\Anaconda3\Scripts\conda.exe' -ArgumentList 'update','anaconda-navigator','-y' -Verb RunAs -Wait
Start-Process -FilePath 'C:\ProgramData\Anaconda3\Scripts\conda.exe' -ArgumentList 'update','--all','-y' -Verb RunAs -Wait
```

**Notes:**
- `-Verb RunAs` triggers UAC prompt — user must click "Yes"
- `-Wait` blocks until the command finishes (important: run sequentially, not in parallel)
- Each command opens a new elevated window; close between runs

## Verification

```powershell
# Check updated version
& 'C:\ProgramData\Anaconda3\Scripts\conda.exe' info | findstr "conda version"
# Before: 26.1.0 → After: 26.1.1

& 'C:\ProgramData\Anaconda3\Scripts\conda.exe' list anaconda-navigator | findstr navigator
```

## When NOT to Use This Fix

- User-level installs (`C:\Users\<user>\Anaconda3\`) — just run `conda update` normally
- If your account is NOT in the Administrators group — RunAs will fail; ask an admin
- Don't use `takeown` or `icacls` on `C:\ProgramData\Anaconda3\` — this breaks Windows trust model and can cause issues with future updates

## Related: Per-Package Workaround

If you just need to install/update a specific package (not conda itself):
```bash
python -m pip install --user --upgrade <package>
# Installs to: %APPDATA%\Python\Python313\site-packages
# No admin needed, but only works for pip packages, not conda packages
```
