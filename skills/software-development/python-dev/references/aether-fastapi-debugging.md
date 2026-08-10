# Aether Desktop App - FastAPI Debugging Notes (2026-07-26)

## Project Paths
- **Source**: `C:\Users\valte\aether\` (main repo)
- **Desktop app entry**: `C:\Users\valte\aether\desktop_app.py`
- **UI assets**: `C:\Users\valte\aether\desktop_ui\`
- **Running venv**: `C:\Users\valte\aether\Aether_1\` (NOT the repo root!)
- **Session store**: `%APPDATA%\aether\sessions\` (e.g., `C:\Users\valte\AppData\Roaming\aether\sessions\`)

## Running the App
```bash
# From repo root (aether/):
cd C:\Users\valte\aether
# Use the VENV python, not system python:
C:\Users\valte\aether\Aether_1\python.exe desktop_app.py
```

## Server Details
- **API port**: 8732 (FastAPI/uvicorn)
- **API base**: `http://localhost:8732/api/`
- **Webview port**: 8732 (same server, serves UI via StaticFiles)

## Session Management
- Sessions stored as JSON files in `%APPDATA%\aether\sessions\`
- File format: `chat_<10-char-hex>.json`
- Fields: `id`, `title`, `messages[]`, `mode` ("normal" | "rag"), `pinned`, `files[]`
- New session endpoint: `POST /api/sessions/new` — accepts `{mode}` in body
- Get session: `GET /api/sessions/{sid}`
- List sessions: `GET /api/sessions`

## Common Debugging Commands
```bash
# Check running Aether processes
tasklist | findstr /i aether

# Check if server is listening on port 8732
netstat -ano | findstr :8732

# Kill stale process on 8732
taskkill /PID <pid> /F

# Test new session with RAG mode
curl -s -X POST http://localhost:8732/api/sessions/new -H "Content-Type: application/json" -d '{"mode": "rag"}'

# View session file
python -c "import json; print(json.dumps(json.load(open(r'C:\Users\valte\AppData\Roaming\aether\sessions\chat_XXXXXXXXXX.json')), indent=2))"
```

## Git-bash Quirks (Critical!)
- **Path doubling**: `cmd /c "C:\Users\valte\cloudflared.exe"` may resolve to `C:\c\Users\valte\cloudflared.exe` — use Python `subprocess.run()` or PowerShell `.ps1` instead
- **File locking**: When uvicorn serves `desktop_app.py`, editing via `patch`/`write_file` may silently fail or leave stale handles — always verify with `python -c "print(open('desktop_app.py').read()[start:end])"`
- **Restart required**: After editing `desktop_app.py`, must restart server (uvicorn doesn't auto-reload in this setup unless `--reload` used)

## Verified Fixes This Session
1. **RAG mode persistence** — `desktop_app.py:290-302` now reads `mode` from request body; `index.html:391-394` sends `{mode}` in POST body
2. **Session mode loading** — `selectSession()` reads `d.mode` from session and updates UI mode toggle