---
name: diagnose
description: Disciplined diagnosis loop for hard bugs and performance regressions. Reproduce → minimise → hypothesise → instrument → fix → regression-test. Use when user says "diagnose this" / "debug this", reports a bug, says something is broken/throwing/failing, or describes a performance regression. Also use when user says "fix yourself", "deep diagnose", "check root cause", or "what's wrong here".
---

# Diagnose

A discipline for hard bugs. Skip phases only when explicitly justified.

## Phase 1 — Build a Feedback Loop

**This is the skill.** Everything else is mechanical. If you have a fast, deterministic, agent-runnable pass/fail signal for the bug, you will find the cause.

### Ways to construct a feedback loop (try in order):

1. **Failing test** — unit, integration, e2e at whatever seam reaches the bug
2. **Curl / HTTP script** against a running dev server
3. **CLI invocation** with fixture input, diffing stdout against known-good snapshot
4. **Headless browser script** (Playwright / Puppeteer) — drives UI, asserts on DOM/console/network
5. **Replay captured trace** — save real network request/payload/event log; replay in isolation
6. **Throwaway harness** — minimal subset of system exercising the bug code path
7. **Property / fuzz loop** — run 1000 random inputs, look for failure mode
8. **Bisection harness** — automate "boot at state X, check, repeat" for `git bisect run`
9. **Differential loop** — run same input through old vs new version, diff outputs
10. **HITL bash script** — last resort, drive human with structured script

### Iterate on the loop itself
- Can I make it faster? (Cache setup, skip unrelated init)
- Can I make the signal sharper? (Assert on specific symptom)
- Can I make it more deterministic? (Pin time, seed RNG, isolate filesystem)

### Non-deterministic bugs
Goal is higher reproduction rate, not clean repro. Loop trigger 100×, parallelise, add stress, narrow timing windows.

### When you cannot build a loop
Stop and say so explicitly. List what you tried. Ask user for: (a) access to reproducing environment, (b) captured artifact (HAR, log dump, core dump), or (c) permission to add temporary instrumentation.

**Do not proceed to Phase 2 until you have a loop you believe in.**

## Phase 2 — Reproduce

Run the loop. Watch the bug appear.

- [ ] Loop produces the failure mode the **user** described
- [ ] Failure is reproducible across multiple runs
- [ ] Exact symptom captured (error message, wrong output, slow timing)

## Phase 3 — Hypothesise

Generate **3–5 ranked hypotheses** before testing any. Each must be **falsifiable**:

> "If <X> is the cause, then <changing Y> will make the bug disappear / <changing Z> will make it worse."

Show ranked list to user before testing — they may have domain knowledge that re-ranks instantly.

## Phase 4 — Instrument

Each probe maps to a specific prediction from Phase 3. **Change one variable at a time.**

Tool preference: Debugger/REPL > targeted logs. Never "log everything and grep".

Tag every debug log with unique prefix, e.g. `[DEBUG-a4f2]`. Cleanup at end = single grep.

For perf regressions: establish baseline measurement first, then bisect.

## Phase 5 — Fix + Regression Test

Write regression test **before the fix** — but only if there's a **correct seam** (exercises the real bug pattern at the call site).

1. Turn minimised repro into failing test
2. Watch it fail
3. Apply fix
4. Watch it pass
5. Re-run Phase 1 loop against original scenario

## Phase 6 — Cleanup + Post-Mortem

- [ ] Original repro no longer reproduces
- [ ] Regression test passes (or absence of seam is documented)
- [ ] All `[DEBUG-...]` instrumentation removed
- [ ] Throwaway prototypes deleted
- [ ] Correct hypothesis stated in commit/PR message

**Then ask: what would have prevented this bug?** If architectural change needed, recommend it after the fix is in.

## Windows/Python Environment Diagnostics Lessons

When diagnosing Windows/Python/environment issues, consider these specific patterns:

**Conda Environment Issues:**
- System-wide conda installations (e.g. C:\ProgramData\anaconda3) are often read-only
- Error: "EnvironmentNotWritableError: The current user does not have write permissions"
- Solution: 
  1. Create user-owned environment: `conda create -p /c/Users/<username>/conda_envs/<envname> python=<version>`
  2. OR fix permissions: `takeown /F "<path>" /A /R && icacls "<path>" /grant "%USERNAME%:(OI)(CI)F" /T`
  3. Always verify which python/pip is being used with `which python` or `where python`

**PyTorch/GPU Setup:**
- Check installed variants: `pip list | grep -i torch` shows +cpu vs +cu121
- For GPU support, install with: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121`
- May need to uninstall CPU versions first: `pip uninstall -y torch torchvision torchaudio`
- Verify with: `python -c "import torch; print('CUDA available:', torch.cuda.is_available())"`

**Browser/CDP Troubleshooting:**
- When standard navigation fails (net::ERR_ABORTED):
  1. Check if MCP server is running: `npx -y chrome-devtools-mcp --browserUrl http://127.0.0.1:9222`
  2. Try to list pages: `mcp_chrome_devtools_list_pages`
  3. If page exists, try to take snapshot or evaluate script
  4. Consider starting MCP server manually if not already running

**MCP Connection Testing Strategy:**
- Test each MCP server individually with appropriate probe commands:
  • Filesystem: `mcp_filesystem_list_directory` <path>
  • GitHub: `mcp_github_search_repositories` <query>
  • Linear: `mcp_linear_list_teams`
  • DuckDuckGo: `mcp_duckduckgo_duckduckgo_web_search` <query> (watch for rate limits)
  • YouTube: `mcp_youtube_download_youtube_url` <url> (requires yt-dlp)
  • SQLite: `mcp_sqlite_list_tables` (check DB file path/permissions)
  • Workflow Engine: status check via `hermes mcp list`

**Windows-Specific Gotchas:**
- Path differences: MSYS (/c/Users/name) vs Windows (C:\Users\name)
- Admin requirements: Some operations need elevated permissions
- Path quoting: Spaces in Windows paths require proper quoting in scripts
