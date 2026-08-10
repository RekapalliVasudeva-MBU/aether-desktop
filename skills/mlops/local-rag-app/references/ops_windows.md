# Ops on Windows (git-bash / MSYS)

## Restart the FastAPI server (PID lives in Windows-native namespace)
git-bash `kill -9 <pid>` and `taskkill //PID <pid> /F` (doubled slash) BOTH fail
because the server runs in the Windows PID space, not the MSYS one. Use:
```bash
cmd.exe /c "taskkill /PID <pid> /F"
sleep 2
netstat -ano | grep ":8000 .*LISTENING" || echo "LISTENER FREE"
```
Then relaunch:
```bash
cd "C:/Users/valte/project_rag" && python server.py   # background=true in agent
```

## ngrok free plan: max 3 simultaneous agent sessions
Symptom: new server logs `ERROR: authentication failed: Your account is limited to 3
simultaneous ngrok agent sessions.` (or `ERR_NGROK_334 ... endpoint already online`
if you try to bind the same URL twice).

Find orphan ngrok tunnels (leftover from earlier `ngrok http` CLI calls this session):
```bash
cmd.exe /c "tasklist | findstr /i ngrok"
netstat -ano | grep -E ":4040 |:4041 |:4042 "   # ngrok local API ports
```
Each ngrok exposes tunnels at http://127.0.0.1:<port>/api/tunnels. Inspect:
```bash
python -c "import urllib.request,json;d=json.loads(urllib.request.urlopen('http://127.0.0.1:4040/api/tunnels').read());[print(t['public_url'],'->',t['config']['addr']) for t in d['tunnels']]"
```
Kill the ORPHAN ones (keep the one forwarding to your server's :8000):
```bash
cmd.exe /c "taskkill /PID <orphan_pid> /F"
```
After cleanup, only the live tunnel remains -> public URL healthy.

## Don't re-bind ngrok on every restart
The existing tunnel forwards to localhost:8000. Restarting the server serves new
code through the SAME public URL. Only re-bind if the tunnel process itself died
(free plan cannot reserve a static domain — use the random URL).

## Hard-refresh after UI change
Even with Cache-Control: no-store, an already-open tab may hold the old DOM. Tell
users: Ctrl+Shift+R (or open in private/incognito). Verify server-side with:
```bash
python -c "import urllib.request;h=urllib.request.urlopen('http://127.0.0.1:8000/').read().decode();print('bgfx' in h, 'cursor-glow' in h)"
```
