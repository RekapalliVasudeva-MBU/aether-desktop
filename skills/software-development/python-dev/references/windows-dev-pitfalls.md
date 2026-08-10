# Windows Development Pitfalls

## FastAPI Server Binding

| Scenario | `host=` value | Browser URL |
|----------|--------------|-------------|
| Local dev | `127.0.0.1` | `http://127.0.0.1:8000` or `http://localhost:8000` |
| Render/cloud | `0.0.0.0` | N/A (cloud router handles it) |

**Never tell users to visit `http://0.0.0.0:8000`** — it triggers `ERR_ADDRESS_INVALID`.

## Port Already in Use (Windows)

```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill it (PowerShell — git-bash mangles /PID flag)
Stop-Process -Id <PID> -Force
```

## Git Operations on Windows

Git-bash/MSYS on Windows causes parsing issues:
- `taskkill /PID 1234 /F` → bash interprets `/PID` as a path → fails
- `git pull --rebase` with untracked files → aborts with confusing errors
- `git push` after manual GitHub web edits → "rejected (fetch first)"

**Preferred approach:** Use `execute_code` tool with Python's `subprocess` for git operations — avoids all shell parsing issues.

```python
import subprocess
result = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True, cwd=project, timeout=120)
```

## Conda Env on Windows

`conda` command is NOT available in git-bash. Use full path to Python executable:

```bash
# Instead of: conda run -n ai_env python app.py
"C:\ProgramData\anaconda3\envs\ai_env\python.exe" app.py
```
