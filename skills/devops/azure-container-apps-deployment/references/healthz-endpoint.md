# Minimal Health Check Endpoint

Add to your FastAPI app for Container Apps liveness probe:

```python
@app.get("/healthz")
async def healthz():
    """Lightweight liveness probe for container orchestration - no DB calls."""
    return {"status": "ok"}
```

**Requirements:**
- Returns 200 OK with JSON body
- No database connections
- No external API calls
- Responds in < 5 seconds
- Path must match `HEALTHCHECK` in Dockerfile (`/healthz`)

**Why not `/api/health`?**
- `/api/health` typically checks DB, queue, model status — too heavy for liveness
- Liveness probe should only verify process is alive
- Readiness probe (if needed) can use `/api/health` for deeper checks