# Process Hygiene & Host-Hermes Caution (Aether desktop-app testing)

## Why this exists
During the v1.2.x launch-debug cycle, leftover background test processes
(`Aether.exe`, `uvicorn`, Playwright/`npx` servers) accumulated on the user's
16 GB machine. The memory/thermal pressure triggered an unexpected reboot the
user blamed on the agent. Separately, a blanket `taskkill /F /IM node.exe`
killed the user's HOST Hermes agent's own MCP servers (they auto-recovered, but
it was a self-inflicted outage). Both are avoidable.

## Rules
1. **Kill your own test servers.** Every background launch for verification
   (`terminal(background=true)` of `Aether.exe` or `uvicorn`) MUST be torn down
   at end of turn — use `notify_on_complete=true` and then
   `process(action='kill')`, or kill by PID. Never leave an `Aether.exe`
   running after the test.
2. **Never blanket-kill node.exe / python.exe.** The user's host Hermes agent
   runs its MCP servers as `node.exe` (github, filesystem, memory, youtube,
   duckduckgo, playwright, etc.) and its core as `python.exe`/`pythonw.exe`
   (`hermes_cli.main gateway|dashboard`, `tui_gateway.slash_worker`). Their
   ParentProcessId points at a host Hermes python, NOT at Aether.
3. **Identify before you kill.** Only terminate PIDs whose command line contains
   `Aether`, `uvicorn`, or `make_installer` (i.e. YOUR test spawns). Inspect:
   ```powershell
   powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"CommandLine LIKE '%Aether%'\" | Select ProcessId,Name,CommandLine | Format-List"
   ```
4. **Port 8732 free ≠ app healthy.** A stale `Aether.exe` can hold the port so a
   new shortcut launch fails its probe. If the shortcut won't open, check
   `tasklist | findstr Aether` and kill the stale PID, then relaunch.
5. **Reboot diagnosis.** If the user reports a restart: check
   `netstat`/`tasklist` for YOUR orphans, check the Windows event log for a
   pending-update `RebootRequired` flag (`HKLM:\...\WindowsUpdate\Auto Update\
   RebootRequired`), and read `%LOCALAPPDATA%\Aether\aether_startup.log` for the
   real crash. Don't assume it was your code — but clean up your procs first.

## Symptom → cause map
- "API did not become ready in time" + port FREE + a stale `Aether.exe` alive
  → old broken instance holding things; kill it, relaunch.
- "API did not become ready in time" + port FREE + no Aether proc + startup log
  shows `isatty`/`Unable to configure formatter` → frozen-exe stdout crash
  (see `aether_frozen_exe.md`, the `isatty` fix).
- System reboot with no `RebootRequired` flag → resource pressure from leftover
  test procs on a small-RAM machine → enforce rule #1 next time.
