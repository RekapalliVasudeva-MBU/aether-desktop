# Verify a frozen Windows app actually launches (no crash)

Use when the user reports "the app won't open" — confirm it's running before
assuming a build defect. This app is a **native pywebview window** (WebView2)
that loads http://127.0.0.1:PORT/ui/ — there is NO browser tab by default
(this user rejected the "localhost website" approach; see the native-window
section in SKILL.md). If the native window can't start, it falls back to opening
the URL in the default browser.

## Kill stale instances
```bat
taskkill /F /IM Aether.exe
```
(Repeated test launches leave 5–7 copies that hold the port and confuse things.)

## Launch + poll (correct way)
Do NOT use `start "" exe &` inside a subshell that returns — the child dies
when the parent shell exits, making a live app look dead. Launch the exe via
`terminal(background=true)` directly, then poll in a separate call:

```bat
netstat -an | findstr :8732
curl -s -o /dev/null -w "ui: %{http_code}\n" http://127.0.0.1:8732/ui/
curl -s -o /dev/null -w "cfg: %{http_code}\n" http://127.0.0.1:8732/api/config
```
`/ui/` → 200 + port listening = the app WORKS.

## Alive-but-exits test
```bat
timeout 15 Aether.exe > log.txt 2>&1
echo %errorlevel%   # 124 = still running at timeout => launched OK, not a crash
```

## SmartScreen (unsigned exe)
If server is up but double-click "does nothing": Windows SmartScreen blocks the
unsigned exe. User clicks "More info → Run anyway" (one-time). Safe — it's
their own build.

## Shortcut target check
```powershell
(New-Object -ComObject WScript.Shell).CreateShortcut('C:\Users\valte\OneDrive\Desktop\Aether.lnk').TargetPath
```
Good target: C:\Users\valte\AppData\Local\Aether\Aether.exe
Bad (dead): C:\Users\valte\AppData\Local\Temp\aether_final2\Aether.exe
Remove dead .lnk files with `rm -f` (powershell Remove-Item hung in this env).
