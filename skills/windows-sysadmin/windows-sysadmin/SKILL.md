---
name: windows-sysadmin
description: Windows system administration — disk cleanup, browser control, file operations, and Windows-specific pitfalls. Covers both CDP-based web element interaction AND physical desktop automation, plus disk space recovery, junk cleanup, and common Windows gotchas (admin requirements, PowerShell quoting, MSYS path issues). Use when the user asks to clean disk space, control their Edge browser, delete junk files, or troubleshoot any Windows-specific operational issue.
---

# Windows Sysadmin

Class-level skill for all Windows system administration tasks. Covers disk cleanup, browser control, file operations, and Windows-specific development pitfalls.

## Table of Contents

1. [Disk Cleanup](#disk-cleanup) — Free disk space, delete junk, remove leftovers
2. [Browser Control](#browser-control) — CDP web interaction + physical cursor control
3. [Windows Dev Pitfalls](#windows-dev-pitfalls) — Common gotchas for dev tools on Windows
4. [Admin & Permissions](#admin--permissions) — What needs admin, what doesn't
5. [Diagnosing "App Won't Open" (Single-Instance Launchers)](#diagnosing-app-wont-open-single-instance-launchers) — server-alive ≠ window-alive, mutex, focus-steal
6. [Cloudflared Tunnel Forensics](#cloudflared-tunnel-forensics) — verify live, find binary/service, recover URL, zombie-service trap

---

## Disk Cleanup

### Safety Rules
1. **NEVER delete without showing the user what will be deleted first** — list paths and sizes
2. **Program Files deletion needs admin** — tell the user upfront with exact commands
3. **Use `execute_code` with Python** for file operations, not bash `rm -rf` (MSYS path issues)
4. **Protected system files**: Never touch `hiberfil.sys`, `pagefile.sys`, `Windows.old` unless user explicitly asks

### Step-by-Step Process

#### 1. Survey — Find the Junk
Use `execute_code` to walk key locations and measure sizes:

```python
import os, shutil

def get_size(path):
    total = 0
    try:
        if os.path.isfile(path):
            return os.path.getsize(path)
        for dp, dn, fn in os.walk(path):
            for f in fn:
                try: total += os.path.getsize(os.path.join(dp, f))
                except: pass
    except: pass
    return total

paths = [
    (r'C:\Users\valte\AppData\Local\npm-cache', 'npm-cache'),
    (r'C:\Users\valte\AppData\Local\pip\cache', 'pip cache'),
    (r'C:\Users\valte\AppData\Local\Temp', 'Temp folder'),
    (r'C:\Users\valte\AppData\Local\Microsoft\Windows\Explorer', 'Thumbnail cache'),
    (r'C:\Users\valte\AppData\Local\Microsoft\Windows\WebCache', 'Web cache'),
    (r'C:\Users\valte\Downloads', 'Downloads'),
    (r'C:\$Recycle.Bin', 'Recycle Bin'),
    (r'C:\$Windows.~BT', 'Windows upgrade backup'),
    (r'C:\$Windows.~WS', 'Windows upgrade staging'),
]
```

#### 2. Check Ollama Partial Downloads
When `ollama pull` fails (e.g., TLS handshake timeout), incomplete blobs remain in `C:\Users\<user>\.ollama\models\blobs\` as `*-partial*` files. These can total 5-10 GB per failed model.

**Detect:**
```powershell
Get-ChildItem "$env:USERPROFILE\.ollama\models\blobs" -Recurse -File | Where-Object { $_.Name -like "*-partial*" } | ForEach-Object { Write-Output "$($_.FullName) => $([math]::Round($_.Length/1MB,1)) MB" }
```

**Clean up (write as .ps1 file, do NOT inline):**
```powershell
$blobs = "$env:USERPROFILE\.ollama\models\blobs"
Get-ChildItem $blobs -Recurse -File | Where-Object { $_.Name -like "*-partial*" } | ForEach-Object {
    Write-Output "Deleting: $($_.Name) => $([math]::Round($_.Length/1MB,1)) MB"
    Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
}
# Remove empty blob directories
Get-ChildItem $blobs -Directory -Recurse | Where-Object { (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue).Count -eq 0 } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
```

**Always use a `.ps1` script file** for this — never inline PowerShell with `$()` in bash/MSYS.

#### 3. Check Specific Leftovers
For software the user previously had installed, search all Adobe/MATLAB/etc. folders:
- `C:\\Program Files\\`, `C:\\Program Files (x86)\\`, `C:\\Program Files\\Common Files\\`
- `C:\\ProgramData\\`
- `C:\\Users\\<user>\\AppData\\Local\\`, `AppData\\Roaming\\`, `AppData\\LocalLow\\`
- `C:\\Users\\<user>\\Documents\\`
- `C:\\Users\\<user>\\Downloads\\` (installers, temp extraction folders)

See [`references/leftover-patterns.md`](references/leftover-patterns.md) for detailed per-software leftover locations (MATLAB, Adobe, npm, eclipse, etc.).
See [`references/ollama-partial-cleanup.md`](references/ollama-partial-cleanup.md) for cleaning up failed Ollama model downloads (`*-partial*` blobs).
See [`references/eclipse-workspace-cleanup.md`](references/eclipse-workspace-cleanup.md) for deleting all Eclipse workspaces, metadata, and installer remnants before a fresh install.

#### 3a. MSIX/WindowsApps Apps (Adobe, etc.) — Registry vs Disk Reality

**Critical:** Apps installed via Creative Cloud or Microsoft Store (MSIX) may show large sizes in Settings > Apps but `C:\Program Files\<App>` appears **empty** when listed from bash/PowerShell. The files are in protected WindowsApps-style locations.

**Detection — always use the registry, not directory listing:**
```powershell
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
                 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*' |
  Where-Object { $_.DisplayName -like '*Adobe*' -or $_.DisplayName -like '*Media*' } |
  Select-Object DisplayName, InstallLocation,
    @{N='SizeMB';E={[math]::Round($_.EstimatedSize/1024,1)}} |
  Format-Table -AutoSize
```

**The `EstimatedSize` value is from the MSI registry, NOT actual disk usage.** The real files may be in protected locations. Always cross-check with `du -sh` on the `InstallLocation` — if it shows 0 or near-0 but the registry says 12GB+, the app is MSIX-packaged.

**Uninstall path for Adobe MSIX apps:** The uninstaller lives in the shared Adobe Desktop Common folder:
```
C:\Program Files (x86)\Common Files\Adobe\Adobe Desktop Common\HDBox\Uninstaller.exe
```
Run with: `--uninstall=1 --sapCode=AME --productVersion=26.0.2 --productPlatform=win64`

**Registry entries persist after uninstall.** After running the uninstaller, `Get-ItemProperty` queries may still show the app in the installed apps list. This is normal — Windows refreshes the list on reboot. Tell the user to reboot to see the final result. The actual disk space is freed immediately after the uninstaller runs; the registry lag is cosmetic.

**After Adobe uninstall:** The shared `C:\Program Files (x86)\Common Files\Adobe` folder (55MB) can be safely removed after all Adobe apps are uninstalled. Use `Remove-Item -Recurse -Force` in PowerShell (not `rd /s /q` — that's CMD syntax and fails in PowerShell). If the folder is locked, a reboot may be needed first.
- `C:\Users\<user>\.cache\huggingface` — HuggingFace model/data cache (often 300MB+, safe to delete)
- `C:\Users\<user>\.cache\chrome-devtools-mcp` — Chrome DevTools MCP cache (safe to delete)
- `C:\Users\<user>\AppData\Local\Temp` — Windows temp (safe to delete, ~700MB typical)
- `C:\Users\<user>\AppData\Local\pip\cache` — pip download cache (safe to delete, ~250MB typical)
- `C:\Program Files (x86)\Common Files\Adobe` — shared Adobe components (55MB, keep if any Adobe app remains)

#### 3. Delete What You Can (User Space)
Safe to delete without admin:
- `AppData\Local\Temp\*`
- `AppData\Local\npm-cache`
- `AppData\Local\pip\cache`
- `AppData\Local\Microsoft\Windows\Explorer\thumbcache_*.db` (~395 MB)
- `Downloads\*.exe` (installers after installation)
- `Downloads\_temp_*` (extracted installer folders)
- `AppData\Roaming\<app>` (app config remnants)

#### 4. Report Admin-Required Deletions
For files in `Program Files`, `ProgramData`, or system dirs, tell the user exactly what to run:
```
Run in Admin Command Prompt:
rmdir /s /q "C:\Program Files\MATLAB\R2026a"
rmdir /s /q "C:\Program Files\Common Files\Adobe"
```

#### 5. Empty Recycle Bin
```python
import subprocess
subprocess.run(['powershell', '-Command', 'Clear-RecycleBin -Force -ErrorAction SilentlyContinue'])
```

#### 6. Verify & Report
- Run `shutil.disk_usage("C:/")` before and after
- Report exact GB freed to the user

### Explorer.exe High RAM / Not Loading

When File Explorer is slow, not loading, or taskbar is unresponsive:

1. `Ctrl+Shift+Esc` → Task Manager → Find **Windows Explorer** (explorer.exe) → Right-click → **Restart**
2. This restarts the shell (taskbar + file explorer) in 2 seconds without rebooting

**RAM Benchmarks:**
- Normal: 50–100 MB
- High (needs restart): 200+ MB
- Critical (340+ MB): Restart explorer.exe immediately

---

## Browser Control

### Two Modes — Know Which One the User Wants

#### Mode A: Web Element Interaction (CDP / Playwright)
User wants you to interact with **web page elements** — click buttons, fill forms, read content, navigate pages.

**Tools:** `mcp_chrome_devtools_*` (preferred for Edge) or `browser_*` built-in tools

**Workflow:**
1. `mcp_chrome_devtools_list_pages` — see current tabs
2. `mcp_chrome_devtools_navigate_page` (type=url) — go to target URL
3. `mcp_chrome_devtools_wait_for` — wait for elements to load
4. `mcp_chrome_devtools_take_snapshot` — get interactive element refs
5. `mcp_chrome_devtools_click` / `mcp_chrome_devtools_fill` / `mcp_chrome_devtools_press_key`

### MCP Server Troubleshooting

Common MCP server issues and their solutions:

#### YouTube MCP Server
- **Issue**: "Error downloading video: Error: spawn yt-dlp ENOENT"
- **Solution**: Install yt-dlp via `python -m pip install yt-dlp`

#### DuckDuckGo MCP Server
- **Issue**: "Error: DDG detected an anomaly in the request, you are likely making requests too quickly."
- **Solution**: Wait between requests or reduce frequency. This is a temporary rate limit.

#### SQLite MCP Server
- **Issue**: "Database error: unable to open database file"
- **Solution**: Check that the SQLite database file exists at the expected path and has proper read/write permissions.

#### Fetch MCP Server
- **Issue**: Server shows as disabled in `hermes mcp list`
- **Solution**: May need explicit enabling if web scraping is required (not needed for most tasks).

#### Chrome DevTools MCP Server (Browser/CDP Connectivity)
- **Issue**: `browser_navigate` fails with `net::ERR_ABORTED` but CDP endpoint (port 9222) is reachable
- **Solution**:
  1. Check if chrome-devtools-mcp server is running: `ps aux | grep chrome-devtools-mcp`
  2. If not running, start it manually: `npx -y chrome-devtools-mcp --browserUrl http://127.0.0.1:9222`
  3. Verify connectivity with MCP browser tools before proceeding
  4. Note: Some sites (like Google) may present CAPTCHAs for automated traffic - consider waiting or alternative approaches

#### General MCP Connectivity
1. Check status: `hermes mcp list`
2. Test specific server: `hermes mcp test <server-name>`
3. Review server logs if available
4. Restart Hermes gateway if needed: `hermes gateway restart`

#### Mode B: Physical Cursor Control (Desktop Automation)
User wants you to **physically move the mouse cursor** on their Windows desktop.

**Tools:** `execute_code` with `ctypes` (no pip install needed):

```python
import ctypes
screen_w = ctypes.windll.user32.GetSystemMetrics(0)
screen_h = ctypes.windll.user32.GetSystemMetrics(1)
ctypes.windll.user32.SetCursorPos(x, y)
ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)  # left down
ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)  # left up
```

See [`references/physical-cursor-control.md`](references/physical-cursor-control.md) for full details including DPI scaling and pyautogui alternative.

### CRITICAL Pitfalls

- **CDP/Playwright do NOT move your physical mouse** — `mcp_chrome_devtools_click` clicks a web element, not the Windows cursor
- **Playwright launches its own Chromium** — never use when the user says "use my Edge"
- **Chrome DevTools MCP connects to existing Edge** — requires `--remote-debugging-port=9222`
- **Cloudflare / bot detection** — CDP navigation can trigger "Verify you are human" challenges. Have the user manually open the site, then use CDP to interact.

### Edge Remote Debugging Setup
1. Close Edge completely (kill all `msedge.exe` in Task Manager)
2. Launch Edge with: `"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222`
3. Verify with: `curl http://127.0.0.1:9222/json/version`

### Decision Tree
```
User says "open X in my browser" or "go to website"
  → Physical mouse? YES → Mode B (ctypes) | NO → Mode A (CDP)
User says "control my cursor" / "click on edge" → Mode B
User says "fill this form" / "click this button" → Mode A (CDP)
User says "use my edge" → mcp_chrome_devtools_* (NEVER mcp_playwright_*)
```

---

## Windows Dev Pitfalls

### Config Editing — Use Python, Never sed
`config.yaml` is protected — `read_file` and `patch` reject edits. **sed corrupts Windows paths** (backslash escapes). Use Python yaml module via `execute_code`:

```python
import yaml
with open(r'C:\Users\valte\AppData\Local\hermes\config.yaml', 'r') as f:
    config = yaml.safe_load(f)
# edit config dict
with open(r'C:\Users\valte\AppData\Local\hermes\config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
```

After config changes: `hermes gateway restart`

### PowerShell Quoting in MSYS/Bash
PowerShell commands with `$` variables and `{ }` expressions get mangled by bash/MSYS. **Fix:** Write `.ps1` files and invoke with `powershell -File`:

### PowerShell `rd` Is NOT the Same as CMD `rd`
In PowerShell, `rd` is an alias for `Remove-Item`, which uses `-Recurse -Force` flags, **not** `/s /q`. This causes `A positional parameter cannot be found that accepts argument '/q'` errors.

**When giving the user deletion commands, match their shell:**
- **CMD (Command Prompt):** `rd /s /q "C:\path"` — works
- **PowerShell:** `Remove-Item -Recurse -Force "C:\path"` — must use this form
- **MSYS/bash:** `rm -rf "/c/path"` — must use this form

**Rule:** If the user pastes a terminal error showing `Remove-Item : A positional parameter cannot be found`, they ran CMD syntax in PowerShell. Give them the `Remove-Item -Recurse -Force` form.

```python
write_file(path="/tmp/check.ps1", content="Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 Name, Id, @{N='MemMB';E={[math]::Round($_.WorkingSet64/1MB,1)}} | Format-Table -AutoSize\n")
terminal(command="powershell -File C:/Users/valte/AppData/Local/Temp/check.ps1")
```

**Rule of thumb:** If the PowerShell command has more than one `$` or any `{ }` expression, use a `.ps1` file.

### GUI Installers from MSYS/Bash — Don't Work

GUI installers (rustup-init.exe, NSIS installers, MSI with GUI) **do not work from MSYS bash**. They spawn windows that are invisible or hang. No output is produced.

**Workarounds:**
1. **Pre-built portable ZIP/AppImage** — preferred. Download and extract, no installer needed. For Tauri/Rust apps (CC Switch, etc.), check GitHub Releases for a `-Windows-Portable.zip` asset first.
2. **MSI silent install** — sometimes works: `cmd /c "msiexec /i file.msi /qn /norestart"` — but **verify files exist afterward** since `cmd /c` produces no output in MSYS. Use Python subprocess to check:
   ```python
   import subprocess
   r = subprocess.run(['cmd', '/c', 'dir', r'C:\\Program Files\\AppName'], capture_output=True, text=True)
   print(r.stdout)  # empty = install likely failed
   ```
3. **PowerShell script file** — for installers that need GUI, write a `.ps1` and tell user to run it in PowerShell.

### Installing Tauri/Rust Desktop Apps — Use Pre-built Releases

When the user asks to install a Tauri/Rust desktop app (CC Switch, etc.):
1. **Always check GitHub Releases first** for a pre-built `-Windows-Portable.zip` or `.msi`
2. Download and extract — done in 2 minutes
3. **Do NOT attempt to build from source** unless the user explicitly asks — building requires Rust toolchain which is a GUI installer that fails from MSYS
4. If only source is available, tell the user the app needs to be built on a system with Rust installed

### OneDrive-Synced Desktop — Wrong Shortcut Location

On many Windows systems, the Desktop is synced to OneDrive. The registry key at
`HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders\Desktop`
points to `C:\Users\<user>\OneDrive\Desktop`, **not** `C:\Users\<user>\Desktop`.

**Always check the registry first** before creating shortcuts:
```python
import subprocess
r = subprocess.run(
    ['reg', 'query', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders', '/v', 'Desktop'],
    capture_output=True, text=True
)
print(r.stdout)  # Shows the actual Desktop path
```

Creating a shortcut at `C:\Users\<user>\Desktop\` when the real Desktop is on OneDrive means the user won't see it.

### Creating Windows Shortcuts from MSYS

`WScript.Shell` COM objects fail inline. Works via Python subprocess with a `.ps1` script file:

```python
import subprocess

ps_cmd = r"""
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("C:\Users\valte\OneDrive\Desktop\App.lnk")
$sc.TargetPath = "C:\Users\valte\App\app.exe"
$sc.WorkingDirectory = "C:\Users\valte\App"
$sc.Description = "App Description"
$sc.Save()
Write-Host "Shortcut created"
"""

# Write to .ps1 file and execute
with open(r"C:\Users\valte\make_shortcut.ps1", "w") as f:
    f.write(ps_cmd)

r = subprocess.run(
    ["powershell", "-ExecutionPolicy", "Bypass", "-File", r"C:\Users\valte\make_shortcut.ps1"],
    capture_output=True, text=True
)
print(r.stdout, r.stderr)
```

Key: write the PowerShell to a `.ps1` file, then invoke `powershell -File script.ps1` via Python `subprocess.run()`. Inline commands with `$` and `{}` get mangled by MSYS.

### MSYS `find` Is Slow on Windows — Target Known Paths First

`find /c -maxdepth 6 -iname "*adobe*" -type d` scans the entire C: drive and can take **minutes**. Always check known locations first with targeted `du -sh` before resorting to broad `find`:

```bash
# Fast — check known locations first
du -sh "/c/Program Files/Adobe" 2>/dev/null
du -sh "/c/Program Files (x86)/Adobe" 2>/dev/null
du -sh "/c/Users/valte/AppData/Local/Adobe" 2>/dev/null
du -sh "/c/Users/valte/AppData/Roaming/Adobe" 2>/dev/null
du -sh "/c/Program Files (x86)/Common Files/Adobe" 2>/dev/null
```

Only use broad `find` as a last resort, and always with `-maxdepth` to limit scope.

### cmd /c Produces No Output in MSYS

`cmd /c "..."` in bash often produces **zero output** even on success. Don't trust silence as failure. Instead, use Python subprocess:

```python
import subprocess
r = subprocess.run(['cmd', '/c', 'dir', r'C:\Users\valte\Desktop'], capture_output=True, text=True)
print(r.stdout)
```

This works reliably where `cmd /c "..."` in terminal() produces nothing.

**GUI apps specifically:** Qt, Tkinter, WPF, and Electron apps on Windows produce ZERO console output by design. They detach from the console immediately. The only way to diagnose them is:
1. `cmd /c "app.exe"` to launch and check exit code
2. `cmd /c "tasklist /FI \"IMAGENAME eq app.exe\""` to check if still running
3. Windows Event Viewer for crash details
4. Log files in `%USERPROFILE%\.\<app>\` or `%APPDATA%`

### FastAPI Server Binding
| Scenario | `host=` value | Browser URL |
|----------|--------------|-------------|
| Local dev | `127.0.0.1` | `http://127.0.0.1:8000` |
| Cloud | `0.0.0.0` | N/A (cloud router) |

Never tell users to visit `http://0.0.0.0:8000` — triggers `ERR_ADDRESS_INVALID`.

### HTML Parsing — No PCRE in MSYS Grep

MSYS/Windows `grep` does **not support PCRE** — lookbehind `(?<=...)`, lookahead `(?=...)`, and `\K` all fail with `grep: lookbehind assertion is not fixed length`.

**Rule:** When parsing HTML from curl, pipe to Python, not grep:

```bash
# BAD (fails on MSYS):
curl -s "URL" | grep -oP '(?<=<h3[^>]*>).*?(?=</h3>)'

# GOOD (works everywhere):
curl -s "URL" | python3 -c "
import sys, re
html = sys.stdin.read()
titles = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
for t in titles:
    clean = re.sub(r'<[^>]+>', '', t).strip()
    if clean: print(clean)
"
```

### Port Already in Use (Windows)
```powershell
netstat -ano | findstr :8000
Stop-Process -Id <PID> -Force
```

### Git Operations on Windows
Git-bash/MSYS causes parsing issues with Windows flags. **Preferred approach:** Use `execute_code` with Python's `subprocess` for git operations.

### Conda on Windows
`conda` command is NOT available in git-bash. Use full path: `"C:\ProgramData\anaconda3\envs\ai_env\python.exe" app.py`

**Common failure: Anaconda Navigator won't start.**
Symptom: `anaconda-navigator` exits immediately with "Please activate the conda root environment properly" — or no error at all (GUI apps don't write to console).

**Root cause:** Anaconda's paths (`C:\ProgramData\anaconda3`, `Scripts`, `Library\bin`, `condabin`) are not in the user's PATH. The `.exe` is a Qt GUI app that requires conda activation first.

**Diagnosis steps:**
1. Check if conda is in PATH: `cmd /c "where.exe conda"` (use `cmd /c` — `where.exe` is not in MSYS bash)
2. Check installation exists: `cmd /c "dir /b C:\ProgramData\anaconda3\Scripts\anaconda-navigator.exe"`
3. Check conda environments: `type C:\Users\<user>\.conda\environments.txt`
4. Try launching with activation: `cmd /c "C:\ProgramData\anaconda3\Scripts\activate.bat root && C:\ProgramData\anaconda3\Scripts/anaconda-navigator.exe"`

**Fixes (pick one):**
- **Recommended:** Use **Anaconda Prompt** from Start Menu (pre-activated environment)
- **Permanent fix:** Add to system PATH:
  - `C:\ProgramData\anaconda3`
  - `C:\ProgramData\anaconda3\Scripts`
  - `C:\ProgramData\anaconda3\Library\bin`
  - `C:\ProgramData\anaconda3\condabin`
- **One-shot:** `cmd /c "activate.bat root && anaconda-navigator.exe"` (run from any cmd window)

**Note:** GUI apps produce ZERO output in MSYS bash. Don't trust silence — use `cmd /c` prefix and check exit codes. If the app is a Qt/PyQt GUI, it may also silently fail if display drivers or OpenGL are unavailable on a headless/server system.

### Cron Job Failure Diagnosis

When a scheduled cron job shows `last_status: error` or doesn't deliver:

1. Read the error transcript at `~/.hermes/cron/output/<job_id>/<timestamp>.md`
2. Common cause: fallback model (in `delegation.model` or `fallback_providers`) is invalid/expired — replace with a working model
3. Verify with `cronjob(action="run", job_id="<id>")`

See [`references/cron-job-diagnosis.md`](references/cron-job-diagnosis.md) for the full diagnosis workflow and Windows-specific path notes.

### Diagnosing Silent GUI App Failures on Windows

When a Windows GUI application starts and immediately exits with no error, no console output, and no window:

**Why it happens:** GUI apps (Qt, Tkinter, WPF, Electron) don't write to stdout/stderr. The `terminal()` tool runs through MSYS/bash which doesn't capture GUI app output. The `&` backgrounding pattern is blocked by the terminal tool.

**Diagnostic approach:**
1. **Check if binary exists:** `cmd /c "dir /b C:\path\to\app.exe"`
2. **Check dependencies:** `cmd /c "where.exe <required-dll-or-exe>"`
3. **Try direct invocation with cmd /c:** `cmd /c "C:\path\to\app.exe"` — this runs in a real Windows cmd context
4. **Check for activation requirements:** Many tools (conda, SDK managers) need their environment activated first
5. **Look for log files:** Check `%USERPROFILE%\.<app>\`, `%APPDATA%\`, `%LOCALAPPDATA%\`, `%TEMP%`
6. **Check Windows Event Viewer** for crash details: `cmd /c "wevtutil qe Application /q:\"[System[Level=1 or Level=2]]\" /c:5 /f:text /rd:true"`
7. **Test with Python import** (for Python-based apps): `cmd /c "python -c \"import module; print('OK')\""`
8. **Check if the process is still running:** `cmd /c "tasklist /FI \"IMAGENAME eq app.exe\""`

**Key insight:** `cmd /c` is your friend for Windows GUI apps. MSYS bash cannot properly launch or debug GUI applications — always route through `cmd /c`.

---

## Diagnosing "App Won't Open" (Single-Instance Launchers)

A user double-clicks the shortcut and **nothing happens** — no window, no error. This is a *fundamental failure* per the user's own rule; treat it as a real bug, not "it's open already." The most common root cause is a **single-instance mutex with a stale/dead instance**.

### The Core Trap: server-alive ≠ window-alive
Many desktop apps (FastAPI + pywebview, Electron, etc.) use a Windows named mutex (`CreateMutexW` with `Global\...`) so only one instance runs. The launcher's "is another instance already running?" check often only pings the HTTP health port. That is **wrong**: a server can keep listening on its port after its WebView/GUI window has crashed or never rendered, leaving the mutex held with **no usable window**. The launcher then assumes the other instance is fine, tries to focus a non-existent window, and silently exits → "app won't open."

**Correct check:** the other instance is "alive/usable" only if BOTH:
1. The health port returns 200, AND
2. An `Aether.exe`-owned **visible** window exists (enumerate by PID + executable name, not by a brittle title string).

If the server is up but no window exists → treat as dead and **take over** (release mutex, start fresh).

### Diagnostic sequence (verified recipe)
See [`references/app-wont-open-diagnosis.md`](references/app-wont-open-diagnosis.md) for the exact commands. Summary:
1. `tasklist | findstr <app>.exe` — is it running?
2. `netstat -ano | findstr :<port>` — is it listening? Note the PID.
3. Enumerate the PID's **windows** with a ctypes `EnumWindows` + `GetWindowThreadProcessId` script. If it owns only helper windows (`GDI+ Window`, `Default IME`) and NO visible app window → the window died; the mutex is stale.
4. `sc qc <ServiceName>` to get the service binary path (if it runs as a service).
5. Kill the stale PID (`taskkill /PID <n> /F`), then the user can relaunch.

### ctypes pitfalls when patching the launcher
- **`GetModuleFileNameExW` lives in `psapi`**, NOT `kernel32`. `ctypes.windll.kernel32.GetModuleFileNameExW` raises "function not found" — load `ctypes.windll.psapi` and call it there. (Used to scope "is this window owned by Aether.exe".)
- **`SetForegroundWindow` is blocked** when the caller isn't the foreground process. Use `AttachThreadInput(my_thread, target_thread, True)` + `ShowWindow(hwnd, 9)` (SW_RESTORE) + `SetForegroundWindow(hwnd)`, then detach. Without this, a second launch silently fails to raise the window.
- **Indentation bug when editing nested callbacks:** a `return True` placed *after* the code that should run (e.g. inside `if not is_aether:` then continuing with `found.append`) makes the append **unreachable dead code**. Always re-read the patched block and confirm the append is outside the early-return branch. Lint passes but the logic is dead.
- Verify fixes with a **real isolated test**, not just lint: extract the predicate function and drive it with synthetic windows (one `explorer.exe`-owned, one `Aether.exe`-owned visible window). Assert it returns True for the latter and False for "server up + no window."

---

## Cloudflared Tunnel Forensics

User wants a local app (e.g. project_rag on :8000) exposed publicly via Cloudflare tunnel. Diagnose before assuming the link works.

### Verify the tunnel is actually live
1. `netstat -ano | findstr :<port>` — local app listening? (e.g. `:8000`)
2. `tasklist | findstr cloudflared` — is the tunnel process running? Note if it's under **Services** (a Windows service, survives reboots) vs a console process.
3. `sc qc Cloudflared` — service binary path + START_TYPE (2 = AUTO_START = survives reboot). This is the reliable way to get the binary path; `wmic` is often absent on modern Windows.
4. Check the service's outbound connection: `netstat -ano | findstr <cloudflared_PID>`. **If there are NO connections to Cloudflare edge (port 7844 / region*.argotunnel.com), the service is a ZOMBIE** — "running" but not tunneling.

### The deleted-config trap
A named tunnel (`cloudflared tunnel create <name>`) stores credentials in `~/.cloudflared/<name>.json` + `config.yml`. If those are **deleted from disk but the service is still "running"**, the tunnel is live only from in-memory state and:
- You **cannot read the public URL** (it's `<uuid>.cfargotunnel.com`, known only to Cloudflare's edge / the deleted creds).
- The service will **fail to start after any reboot** (binary/config gone).

Discovery limits: the running binary does NOT expose a local admin API port by default, and `Get-CimInstance Win32_Process` returns empty `ExecutablePath`/`CommandLine` for `LocalSystem` services. So you generally **cannot recover the URL** without the Cloudflare API token or the creds file.

### Recovery (needs user confirmation — binary download)
Reinstall `cloudflared.exe` (official Cloudflare binary) + recreate the named tunnel with a `config.yml`, then `cloudflared tunnel install <name>` as a Windows service. This needs a download — **confirm with the user first** (their hard rule: no downloads without explicit OK). A quick tunnel (`cloudflared quick` / `--url`) gives a live URL immediately but regenerates each restart.

See [`references/cloudflared-tunnel-forensics.md`](references/cloudflared-tunnel-forensics.md) for the full command set and the PowerShell-vs-MSYS path quirks that bit during diagnosis.

### MSYS path quirk (bit during this work)
`cmd /c "C:\Users\valte\cloudflared.exe ..."` from git-bash **doubles the drive prefix** → `C:\c\Users\valte\...` and fails. The binary is actually at `C:\Users\valte\cloudflared.exe`. To run a Windows binary reliably from this shell, use Python `subprocess.run([r"C:\Users\valte\cloudflared.exe", ...])` or a `.ps1` file invoked via `powershell -File`. Avoid bare `cmd /c "<backslashed-path>"`.

---

## Admin & Permissions

### What Needs Admin — Tell User Immediately
Files in these locations **always need admin**:
- `C:\Program Files\`, `C:\Program Files (x86)\`, `C:\Program Files\Common Files\`
- `C:\ProgramData\`

**Don't** try takeown, icacls, MoveFileEx, or scheduled tasks — all need admin.
**Do** give the user exact `rmdir /s /q "path"` commands.

### What Needs Admin — No Workaround
- Files in `C:\Program Files`, `C:\Program Files (x86)`, `C:\Program Files\Common Files`, `C:\ProgramData`
- `takeown`, `icacls`, `MoveFileEx`, scheduled tasks — **all need admin**
- Tell the user immediately which folders need admin and give exact commands

### What NOT to Touch
- `hiberfil.sys` (6+ GB) — Windows hibernation
- `pagefile.sys` (17 GB) — Windows virtual memory
- `C:\Windows\` — never touch
- Active program folders

---

## Reference Files

See [`references/leftover-patterns.md`](references/leftover-patterns.md) for detailed per-software leftover locations (MATLAB, Adobe, npm, eclipse, etc.).
See [`references/ollama-partial-cleanup.md`](references/ollama-partial-cleanup.md) for cleaning up failed Ollama model downloads (`*-partial*` blobs).
See [`references/eclipse-workspace-cleanup.md`](references/eclipse-workspace-cleanup.md) for deleting all Eclipse workspaces, metadata, and installer remnants before a fresh install.
- [`references/physical-cursor-control.md`](references/physical-cursor-control.md) — ctypes mouse control, DPI scaling, pyautogui alternative
- [`references/cron-job-diagnosis.md`](references/cron-job-diagnosis.md) — Cron job failure diagnosis: reading error transcripts, model fallback chains, Windows paths
- [`references/docker-windows.md`](references/docker-windows.md) — Docker on Windows: status checks, GPU passthrough, volume mounts, common commands, pitfalls
- [`references/cc-switch-windows.md`](references/cc-switch-windows.md) — CC Switch app: installation, "commits behind" display quirk, data locations
- [`references/anaconda-navigator-debug.md`](references/anaconda-navigator-debug.md) — Anaconda Navigator: won't start, "activate root environment" error, PATH fix, silent GUI app diagnosis
- [`references/app-wont-open-diagnosis.md`](references/app-wont-open-diagnosis.md) — Single-instance launcher "app won't open": server-alive ≠ window-alive, mutex/stale-instance, ctypes focus fixes
- [`references/cloudflared-tunnel-forensics.md`](references/cloudflared-tunnel-forensics.md) — Cloudflared tunnel: verify live, find binary/service, zombie-service trap, URL recovery limits, MSYS path quirks
