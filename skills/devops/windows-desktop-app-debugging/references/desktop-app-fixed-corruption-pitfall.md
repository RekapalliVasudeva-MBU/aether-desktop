# Source File Corruption Pitfall (2026-07-31)

## Problem

A Python `text.replace(old_string, new_string)` call where `old_string` doesn't exactly match the file content (whitespace, encoding, CRLF vs LF line endings) can silently truncate a file to 0 bytes.

## How It Happened

In 2026-07-31, a Python script attempted to patch `desktop_app_fixed.py` using `text.replace()` but the `old_string` contained `\n` characters that didn't match the file's actual CRLF line endings. The replacement failed silently, then the script wrote the (empty or modified) `text` variable back to disk, truncating the file to 0 bytes.

## Root Cause

The script did:
```python
with open(path, 'r') as f:
    text = f.read()
text = text.replace(old_string, new_string)  # old_string not found → text unchanged
with open(path, 'w') as f:
    f.write(text)  # writes empty/unexpected content
```

If `old_string` contains `\n` but the file has `\r\n`, or if the `old_string` is at the wrong position, `replace` returns the original string unchanged. The script then overwrites the file with whatever `text` is — which could be empty if the script constructed it wrong.

## Prevention

1. Read file in binary mode to preserve exact content: `content = open(path, 'rb').read()`
2. Check file size BEFORE and AFTER any patch: `assert len(content) > 0`
3. Backup before patching: `shutil.copy2(path, path + '.bak')`
4. Use `replace_all=True` only when you intend to replace every occurrence
5. Verify the patch applied by checking for the new_string in the result

## Recovery Pattern

When `desktop_app_fixed.py` IS corrupted to 0 bytes:

```powershell
# desktop_app_impl.py has the working architecture (GET / route, /ui/ StaticFiles)
cp desktop_app_impl.py desktop_app_fixed.py
python build_exe.py
```

## Verify After Patching

```powershell
# Check file is not empty after any Python patching script
Test-Path desktop_app_fixed.py
(Get-Item desktop_app_fixed.py).Length -gt 0
```