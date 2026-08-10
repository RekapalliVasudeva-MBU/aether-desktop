# cloudflared tunnel (free public URL for a local server)

## When to use
Public URL for a laptop-hosted local server (RAG website, desktop app backend)
without the ngrok free **monthly bandwidth cap** (which causes `ERR_NGROK_725`
and "Couldn't download — No permissions" on large file downloads).

## The recurring failure (READ THIS FIRST)
The user's #1 complaint: *"u said u deployed it permanently but its not opening."*
Root cause is ALWAYS one of:
1. **Quick tunnel + `start /min cmd /c cloudflared …`** — the child dies when the
   agent/terminal session that launched it ends, AND the URL is **random, changes
   every restart**. So "permanent" was a lie. This pattern must NOT be used for
   anything the user expects to stay up.
2. **`cloudflared` not in PATH** — user runs it from `C:\Windows\system32` in
   PowerShell and gets `not recognized`. The binary is at `C:\Users\<user>\cloudflared.exe`.
   Always give the FULL path: `C:\Users\valte\cloudflared.exe …`.
3. **`tunnel login` wrote no cert** — login run from PowerShell left `.cloudflared/`
   empty (HOME mismatch). Re-run from the agent's MSYS shell where `HOME=C:\Users\<user>`
   so the cert lands in `C:\Users\<user>\.cloudflared\cert.pem`.

## HARD BLOCKERS discovered (this user's account) — patch the "no domain needed" claim
The skill summary says a named tunnel needs "no domain purchase". That is
ONLY true if the Cloudflare account already has >=1 zone. For a
**zero-zone account** (free account with no domains added), the named-tunnel
path is FULLY BLOCKED by three independent walls:

1. **`cloudflared tunnel login` forces a zone pick with NOTHING to
   pick.** When the account has 0 zones, the browser login screen shows
   "select the zone you want to add a Tunnel to" with an empty list and no
   Skip. You CANNOT proceed → `cert.pem` is never written → every later
   `tunnel create` / `tunnel install` fails with "Cannot determine default
   origin certificate path". Re-running login from a clean shell does NOT fix it
   (the zone picker is the wall, not HOME/cert path).
2. **API token cannot create tunnels (by design).** Even with a valid
   `Account → Cloudflare Tunnel → Edit` token (`/tokens/verify` = active,
   `GET /tunnels` = 200):
   - `cloudflared tunnel login --token <X>` → flag rejected ("--loginURL value").
   - `POST /accounts/{id}/tunnels` → 403 Authentication error (the
     cf-v1 tunnel-create endpoint requires the cert from browser login, not an
     API token). So "create the tunnel via the API to bypass the zone screen"
     does NOT work.
3. **`cloudflared tunnel service install` needs ADMIN.** On a non-admin
   shell it fails: "Cannot establish a connection to the service control
   manager: Access is denied." The agent's terminal is non-admin, so the
   agent CANNOT install the service itself — the USER must run it elevated.

Net result for a zero-zone account: the only thing that works is the
**quick tunnel** (`cloudflared tunnel --url http://localhost:8000`), which
gives a random `*.trycloudflare.com` URL, dies when its parent session
ends, and rotates on every restart. There is NO fixed-URL path without
either (a) adding a free zone/domain to Cloudflare, or (b) admin.

### What to actually tell the user on a zero-zone account
- Option A (fixed URL, needs 1 free domain): add a free domain/zone to
  Cloudflare (the "Add a site" screen they kept avoiding IS required for a
  fixed URL — but with a free domain, not a paid one). Then `tunnel login`
  zone picker has something to select, cert writes, and named-tunnel +
  `tunnel install` (run elevated by the user) gives one permanent URL.
- Option B (always-up, needs admin, rotating URL): user opens PowerShell
  AS ADMINISTRATOR and installs the service. **CRITICAL SYNTAX** (see
  "service install syntax trap" below) — the positional-URL form is REJECTED.
  After install, `net start cloudflared`. Auto-restarts on boot. URL still
  rotates per reboot, but comes back UP with no manual step.
- Option C (do nothing): keep using the current quick-tunnel url; relaunch
  when it dies.

### `service install` SYNTAX TRAP (hit 3× this session — durable)
`cloudflared service install http://localhost:8000` is REJECTED with:
`Provided tunnel token is not valid (illegal base64 data at input byte 4).`
The positional `http://...` is parsed as a TUNNEL TOKEN, not a URL.

**Two working forms (use ONE):**
1. **With `--url` flag (explicit):**
   ```
   C:\Users\valte\cloudflared.exe service install --url http://localhost:8000
   ```
2. **Config-file method (bulletproof, no flag ambiguity):**
   Create `C:\Users\valte\.cloudflared\config.yml`:
   ```yaml
   url: http://localhost:8000
   ```
   Then run (no URL on command line at all):
   ```
   C:\Users\valte\cloudflared.exe service install
   ```
   This reads `url:` from the config and works even when `--url` parsing is
   flaky. **This is the form that finally succeeded this session.**

After `service install` succeeds ("Agent service for cloudflared installed
successfully"), START it as a SEPARATE command (NOT `cloudflared service
start` — that's not a valid subcommand; use Windows' own `net`):
```
net start cloudflared
```
`net` is a standalone Windows command — do NOT prefix it with the exe path
(`C:\Users\valte\cloudflared.exe net start ...` glues into one bad command).

### THE BACKEND SERVER MUST ALSO AUTO-START (easy to forget)
The tunnel service coming up is NOT enough — if the local server on :8000 is
down, the public URL returns nothing (connection refused / blank). This
session: tunnel installed + running, but `project_rag/server.py` had exited →
link was dead until `python server.py` was restarted. For genuine permanence
after a reboot, the backend server must ALSO be a Windows service (or started
by the same mechanism), not just the tunnel. Tell the user: "the tunnel is up,
now make sure your server auto-starts too, or the link is dead."

### Exact paste sequence that worked (zero-zone, admin, config-file method)
User in PowerShell AS ADMINISTRATOR, line by line:
```
C:\Users\valte\cloudflared.exe service install
net start cloudflared
```
(config.yml already present with `url: http://localhost:8000`).
Result: service STATE=4 RUNNING, public `*.trycloudflare.com` URL live.

Do NOT promise "one fixed URL forever, no steps" to a zero-zone account —
that combination is impossible without a domain or admin.

## PERMANENT fix: named tunnel + Windows service (use this for real deployments WITH a zone)
Gives ONE fixed URL (e.g. `https://aether-rag.trycloudflare.com`) that never
changes, and auto-starts on boot. Requires the account to have >=1 zone.

### Step 1 — login (user does the browser step, ONE time)
```
C:\Users\valte\cloudflared.exe tunnel login
```
Prints a `dash.cloudflare.com/argotunnel?…` URL. User opens it, logs into
their (free) Cloudflare account, clicks **Authorize**. Cert saves to
`C:\Users\valte\.cloudflared\cert.pem`.
- Run the login from the agent terminal (HOME correct) OR have the user run it from
  PowerShell with the full exe path. If `tunnel list` still says "Cannot determine
  default origin certificate path" after login, the cert won't persist → re-run from
  the agent shell.
- Keep the login command running (it blocks waiting for auth). If the agent's
  `terminal` call times out at 60s, launch it detached:
  `(./cloudflared.exe tunnel login > login_wait.log 2>&1 &)` then poll for the cert
  file to appear.

### Step 2 — create the named tunnel (agent, automatic)
```
C:\Users\valte\cloudflared.exe tunnel create aether-rag
```
Mints a fixed tunnel UUID. Note the `*.trycloudflare.com` hostname it prints.

### Step 3 — install as a Windows SERVICE (permanent, survives reboots — needs ADMIN)
```
C:\Users\valte\cloudflared.exe tunnel install aether-rag
C:\Users\valte\cloudflared.exe tunnel route dns aether-rag <subdomain>.trycloudflare.com   # optional, needs a zone
C:\Users\valte\cloudflared.exe tunnel ingress aether-rag http://localhost:8000
C:\Users\valte\cloudflared.exe tunnel start aether-rag
```
- `tunnel install` registers it as a service that **auto-starts on boot** — the user
  never relaunches it. This is the actual "permanent deployment."
- The fixed URL is now stable across reboots. No more "why is it down."
- NOTE: `tunnel install` / `tunnel service install` require administrator.
  The agent cannot run these; the USER must open PowerShell as Admin.

### Step 4 — verify
```
curl -s -o /dev/null -w "%{http_code}" https://<your-fixed>.trycloudflare.com/
# expect 200
```

## TEMPORARY only: quick tunnel (do NOT promise permanence)
```
C:\Users\valte\cloudflared.exe tunnel --url http://localhost:8000
```
Prints `https://<random>.trycloudflare.com` → HTTP 200. Use ONLY for a quick
test. The URL rotates every restart and the process dies with its parent session.
Never tell the user this is "deployed permanently."

## Don't serve big binaries through the tunnel
Make the download route a **302 redirect to GitHub Releases** (free CDN):
```python
@app.get("/download/aether")
async def download_aether():
    return RedirectResponse(
        "https://github.com/<user>/<repo>/releases/download/v1.0.1/Aether-Setup.exe",
        status_code=302)
```
Removes the bandwidth burn entirely.

## Pitfalls summary
- ❌ `start /min cmd /c cloudflared.exe tunnel --url …` → dies on session end, random URL.
- ❌ Promising "permanent" on a quick tunnel.
- ❌ Running `cloudflared` without the full path from a wrong CWD.
- ❌ `tunnel login` from PowerShell with mismatched HOME (no cert saved).
- ❌ Zero-zone account: named-tunnel path fully blocked (zone picker / API-403 / admin).
- ❌ `tunnel install` / `service install` from a non-admin shell (Access denied).
- ✅ Named tunnel + `tunnel install` (service, run as Admin) = fixed URL + auto-boot = real permanence (needs >=1 zone).
- ✅ Quick tunnel = working URL NOW, but rotating + dies on session end.

## Credential-dead loop — STOP validating, just build it (USER-BEHAVIOR RULE)

When the user pastes an authtoken / API key and says *"use this, just make it
live"* / *"don't ask, build it"* / *"u idiot just deploy it"*, the failure mode
this session actually hit was: the agent re-tested the same (dead) token 4–5
times across ngrok + Cloudflare, printing "invalid token" each time and asking
for a new one — instead of just getting a link up. The user explicitly
corrected this (*"find the issue and fix it"*, *"dont hallucinate u are not
doing what i said"*).

**Rule:** if a tunnel provider's credential fails validation, DO NOT loop on it
and DO NOT keep asking the user for a fresh token. Take the path that works
**with zero credentials** to get a real public link NOW, then offer the
permanent/tokened path as a follow-up:

- **Cloudflare quick tunnel needs NO token** → `cloudflared tunnel --url
  http://localhost:8000` gives a live `https://<random>.trycloudflare.com`
  immediately. This is the escape hatch. Use it the moment a pasted token
  fails. (ngrok free and localhost.run now both require their own auth/key, so
  Cloudflare quick tunnel is the reliable tokenless option.)
- Only AFTER the link is live, tell the user: "this URL rotates on restart;
  for a fixed URL give me a valid Cloudflare token (or add a free zone)."
- If you must verify a token, do it ONCE via the provider's API/agent. If it
  returns "properly formed but invalid" (ngrok `ERR_NGROK_107` / `ERR_NGROK_203`,
  Cloudflare `9109`/`1000`), that's a revoked/reset credential — stopping and
  re-pasting it won't help. Switch to the tokenless path.

This also applies to the general "user is frustrated the agent is stalling"
signal: lead with a working result, explain after.

## Windows git-bash diagnosis pitfalls (cost many turns this session)

Running these from the Hermes terminal (git-bash/MSYS on Windows) has traps:

- **`C:\c\Users\...` double path prefix.** `cmd /c "dir /s /b C:\Users\valte\file"`
  from git-bash rewrites the absolute path and returns `C:\c\Users\valte\file`
  (git-bash prepends `C:\` again). So `dir` "finds" the file at a bogus path.
  Fix: run `cmd /c` commands that don't rely on the returned path string, or
  use bash `ls`/`find` directly. MSYS mounts `C:` as `/c`, so prefer
  `/c/Users/valte/...` in bash-native commands.
- **`sc qc <service>` to get the binary path.** When a tunnel/service is
  running and you need its exe location: `cmd /c "sc qc Cloudflared"` →
  `BINARY_PATH_NAME : C:\Users\valte\cloudflared.exe`. This is the reliable way
  to learn where a service's binary lives (wmic is often unavailable).
- **PowerShell inline quoting fails.** `cmd /c "powershell -Command \"...\" "`
  mangles nested quotes. Fix: write the PowerShell to a temp `.ps1` file
  (`write_file`) and run `cmd /c "powershell -NoProfile -ExecutionPolicy Bypass
  -File C:\path\probe.ps1"`. Use this for `Get-CimInstance`, `Get-EventLog`,
  `WScript.Shell` shortcut inspection, etc.
- **`taskkill` syntax.** Use `taskkill /PID <pid> /F` (single slash). `//PID`
  is rejected. `tasklist | grep -i <name>` confirms running processes.
- **`netstat -ano | grep :<port>`** shows listeners + the owning PID; pair with
  `taskkill /PID` to free a stuck port (e.g. a zombie Aether.exe holding :8732).
- **EnumWindows / ctypes in Python** for window-enumeration diagnostics works
  from the agent's Python (see single-instance-mutex.md). To enumerate a
  process's visible windows: `GetWindowThreadProcessId` per hwnd, filter
  `IsWindowVisible`, scope by exe name via `psapi.GetModuleFileNameExW`
  (load `ctypes.windll.psapi`, NOT `kernel32.GetProcessImageFileNameW` which is
  unresolvable).
- **Service "running" ≠ tunnel working.** A service can be in STATE=4 RUNNING
  but its binary/config deleted from disk (zombie) — netstat shows NO
  connections for its PID. Always verify the public URL with a real
  `curl https://<url>/` (expect 200 + correct page title), not just "process
  exists."

## Note on hosting model
cloudflared is a SECURE PIPE to the laptop — NOT a host. The site is live only
while the laptop is on + server running + tunnel up. Nothing can serve it while the
laptop is fully off/sleeping without paying for separate cloud hosting. The
"permanent" fix = fixed URL + auto-start on boot, not 24/7 uptime with the
laptop closed.
