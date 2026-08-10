# ngrok free tier — what works, what doesn't

## Tokens (two different things)
- **Authtoken** (e.g. `3GLr...`): used by the `pyngrok`/`ngrok` client to *connect a tunnel*.
  This is what `ngrok.set_auth_token(token)` / `server_config.json["ngrok_auth_token"]` needs.
  Free tier connects fine with this.
- **API key** (e.g. `3GM0...`): used by the ngrok *REST API* (reserve domains, manage agents).
  Different credential. Does NOT connect tunnels.

## Static / reserved domains — CAN be reserved on FREE (corrected)
- **Corrected (this session):** a reserved *static* domain CAN be created on the **free** plan
  via the ngrok dashboard (Edge → Domains → "Create a free static domain"). It is a
  `*.ngrok-free.dev` (NOT `.ngrok-free.app`) and survives server restarts (URL does NOT
  change). This user's `marshy-ancient-rebuild.ngrok-free.dev` is one such free static domain.
- The OLD belief that static domains require paid was WRONG — remove it anywhere it appears.
- What is NOT free: paid-only features behind the API key (agent pools, paid edge modules).
  A single static domain + one tunnel is fine on free.
- Random/non-reserved free URLs DO change every restart — but if you reserve the free static
  domain once, you never restart into a new URL.

## Practical
- Wire only the authtoken into `server_config.json["ngrok_auth_token"]`; set
  `ngrok_static_domain` to the reserved free `*.ngrok-free.dev` value.
- Don't propose paid plans to this user (cost-conscious; refuses to pay for groq/ngrok).
- **Restart lock gotcha:** after killing `python server.py`, the OLD tunnel endpoint stays
  "online" in ngrok cloud for a grace period, so a relaunch fails with `ERR_NGROK_334`
  (endpoint already online) and the public URL 502s until ngrok releases it. Kill all
  `ngrok.exe` procs + the old server PID, wait ~30–60s, then relaunch. See the SKILL.md
  "ngrok restart lock" pitfall.
- Verify public reachability: `curl -s https://<id>.ngrok-free.dev/api/health`
  (note: MSYS `curl` sometimes returns 0 bytes on the ngrok TLS path — use python
  `urllib.request` to confirm instead).

## INVALID TOKEN DIAGNOSIS (this session — decisive recipe)
When the user pastes an ngrok token, DO NOT trust it and DO NOT test it against the wrong
API. Verify it the way the agent actually uses it, and read the real auth result.

**Symptom of a dead token:** `ngrok http 8000` exits with
`ERR_NGROK_107` — *"The authtoken you specified is properly formed, but it is invalid."*
ngrok lists exactly why: reset, removed from team, or explicitly revoked. A token that is
"properly formed" still fails if it is stale/revoked.

**Common mistake that wastes cycles:** testing an *agent authtoken* by hitting
`api.cloudflare.com` (wrong service!) or `api.ngrok.com/accounts/me` with a `Bearer` header.
- Against Cloudflare → `code 9109 / 1000 Invalid access token` (tells you nothing useful, and
  it's the WRONG service if the user said ngrok).
- Against `api.ngrok.com` with the agent authtoken as a Bearer → `ERR_NGROK_203` (properly
  formed but invalid) — also tells you nothing about tunnel capability, because the REST API
  key and the agent authtoken are DIFFERENT credentials.

**Correct verification (the only one that matters):**
```bash
# 1. save the token the way the agent uses it
./ngrok.exe config add-authtoken <PASTED_TOKEN>
# 2. actually try to open a tunnel and watch the log for ERR_NGROK_107
timeout 12 ./ngrok.exe http 8000 --log=stdout 2>&1 | grep -iE "ERR_NGROK_107|session established|started tunnel"
```
If you see `ERR_NGROK_107` → the token is invalid/revoked. STOP and ask the user for a FRESH
token from https://dashboard.ngrok.com/get-started/your-authtoken. Do NOT loop on variations,
and NEVER fabricate a "live link".

**This session's exact failure:** user pasted two tokens, labeled one "authtoken" and one
"api key". Both returned `ERR_NGROK_107` (invalid/revoked). He had also earlier said to use
ngrok, NOT Cloudflare — testing them against Cloudflare's API first was a wrong turn that
burned iterations. Lesson embedded in SKILL.md: use the service the user named, and verify the
credential via that service's own agent path before announcing success.

**Binary download (permitted when user says "do whatever / make it live"):**
```bash
curl -sL -o ngrok.zip https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip
unzip -o ngrok.zip -d C:/Users/valte
# -> C:\Users\valte\ngrok.exe
```
**Get the live URL once the tunnel is up:**
```bash
# MSYS curl can return 0 bytes on the ngrok TLS URL — use python:
python -c "import urllib.request,json; d=json.load(urllib.request.urlopen('http://127.0.0.1:4040/api/tunnels')); [print(t['public_url'],'->',t['config']['addr']) for t in d['tunnels']]"
```
