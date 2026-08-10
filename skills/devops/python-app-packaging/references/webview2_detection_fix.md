# WebView2 Detection Fix - Registry Key Correction

## Problem
The app kept showing "WebView2 runtime missing — attempting install" even though WebView2 was installed (verified: version 150.0.4078.99 at `C:\Program Files (x86)\Microsoft\EdgeWebView\Application`).

Root cause: `_webview2_installed()` checked the wrong registry key:
- **Wrong**: `HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications`
- **Correct**: `HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}`

The Evergreen runtime registers at the EdgeUpdate\Clients key with the fixed GUID.

## Verification
```powershell
# This works - WebView2 is installed
Get-ItemProperty 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
# Returns: pv = 150.0.4078.99

# This fails - wrong key
Get-ItemProperty 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeWebView\Applications'
# Returns: nothing (key doesn't exist)
```

## Fix Applied
Updated `_webview2_installed()` in `desktop_app.py` to check the correct registry key first, then fall back to the alternate key and side-by-side DLL check.

## Rebuild Required
```bash
cd C:/Users/valte/aether && python build_aether.py
# Then copy to install location:
Copy-Item -Path "C:\Users\valte\aether\dist_build\Aether\*" -Destination "C:\Users\valte\AppData\Local\Aether\" -Recurse -Force
```