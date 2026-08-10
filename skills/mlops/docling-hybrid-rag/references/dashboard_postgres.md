# Owner dashboard + daily snapshot (Postgres telemetry)

## Postgres schema (rag_site)
```sql
CREATE DATABASE rag_site;
\c rag_site
CREATE TABLE visitor_logs (
    id SERIAL PRIMARY KEY,
    session_id TEXT,
    project TEXT,
    event TEXT,            -- 'question' | 'answer' | 'error' | 'download' | 'waitlist_signup'
    detail TEXT,
    ts TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE waitlist (
    email TEXT PRIMARY KEY,
    name TEXT,
    note TEXT,
    ts TIMESTAMPTZ DEFAULT NOW()
);
```
- Connect with psycopg2: `psycopg2.connect("dbname=rag_site user=postgres password=... host=127.0.0.1 port=5432")`.
- `visitor_logs` writes ONLY when laptop is on. If connect fails, set `enabled=False`
  and the site still serves (logging skipped) — privacy rule: laptop off => no data.

## today_stats() helper (server side)
Returns:
```python
{"enabled": True, "visits": int, "questions": int, "waitlist": int,
 "recent": [{"ts","project","event","detail"}], "waitlist_rows": [{"name","email","note","ts"}]}
```
- counts use `WHERE ts >= CURRENT_DATE`.
- recent = last 50 rows ordered by ts desc; waitlist_rows = all signups desc.

## /dashboard route (localhost-only)
```python
@app.get("/dashboard")
async def dashboard(request: Request):
    client = request.client.host if request.client else ""
    if client not in ("127.0.0.1", "::1", "localhost"):
        return JSONResponse({"error": "owner-only"}, status_code=403)
    return HTMLResponse(_render_dashboard(store.today_stats()))
```
- No auth (owner-only by source IP). Render a simple Tailwind HTML table.

## Daily cron (Hermes)
- A no-agent script job. `script` MUST be a bare filename under `~/.hermes/scripts/`
  (absolute paths are rejected). Use a thin wrapper there that calls the real
  project script (which hardcodes its own PROJECT_DIR).
- `dashboard_daily.py` writes `dashboard_log/dashboard_YYYY-MM-DD.md` + `.json`.
- MUST handle Postgres-off: write "no data (laptop off?)" snapshot, exit 0.

## Verified concurrency
- 20 simultaneous requests through the serial queue: all 20 answered (fail=0) in ~98s.
- Capacity = one local model call at a time; the answer cache makes repeat questions free.
