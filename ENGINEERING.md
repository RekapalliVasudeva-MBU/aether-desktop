# Engineering Guide — Aether

How we build Aether. Distilled from the [gstack](https://github.com/garrytan/gstack)
methodology (plan → review → ship) and adapted to this repo.

> This is the operating manual for anyone (human or AI agent) working on Aether.
> Follow it.

## Principles

- **Boil the Ocean.** AI makes completeness cheap. Do the complete thing: cover
  edge cases, error paths, and tests. The only out-of-scope work is unrelated
  rewrites — flag those as separate scope.
- **Search Before Building.** Reuse what exists in `aether/` before adding new
  code. Three layers: tried-and-true → new/popular (scrutinize) → first principles.
- **User Sovereignty.** Irreversible or taste calls (force-push, MAJOR/MINOR
  version bump, deleting data, cutting scope) are the user's to make. Present the
  tradeoff + recommendation, then let them choose.
- **Iron Law of Debugging.** No fix without a root cause. Diagnose the *why* before
  editing. 3+ failed fixes on the same symptom → question the architecture.

## Repo layout (what to touch)

```
aether/
  desktop_app.py        # FastAPI app + pywebview window (entry point)
  aether/
    agent.py            # LLM agent loop, tool dispatch
    tools.py            # tool implementations (web_search, file, exec…)
    skills.py           # agent skill/prompt registry
    rag.py              # ChromaDB RAG retrieval
    compression.py      # context compaction (preserve_last_n + tool-output Snip cap)
    memory.py           # session/long-term memory
    mcp.py              # MCP client
    provider.py         # model provider abstraction
    gateway_ctl.py      # external gateway control (Telegram etc.)
    pdf_store.py        # PDF ingestion into ChromaDB
    config.py           # config loading
  aether_cli.py         # CLI entry
  make_installer.py     # Inno Setup installer build
  Aether.spec / Aether-Setup.spec   # PyInstaller specs
```

Build artifacts (`build/`, `dist/`, `dist_build/`, `build_aether/`, `*.log`) are
**not** source. Never commit them.

## Investigate (debugging)

1. **Investigate** — reproduce. Capture the exact error, stack trace, inputs, OS.
   Read the code path. Do not mutate yet.
2. **Analyze** — rank hypotheses by likelihood; trace the data flow.
3. **Hypothesize** — state the root cause in one testable sentence.
4. **Implement** — minimal fix for the root cause, not the symptom.

Rules: touch only files related to the root cause; re-run the repro with fresh
passing evidence; `git revert` on regression; stop and ask if >5 files without a
clear root cause.

## QA (verifying the app works)

Aether is a desktop app (FastAPI backend + WebView frontend). Test both:

- **Backend:** start `desktop_app.py`, hit the real endpoints (`/api/sessions`,
  RAG query, etc.) with `curl`/browser. Check console for errors.
- **Frontend:** open the app window; click through Sessions, Chat, Settings,
  ingest. Screenshot before/after.

Tiers: **Quick** (critical+high), **Standard** (default, +medium), **Exhaustive**
(+low/cosmetic). Diff-aware: when verifying a branch, scope to `git diff main...HEAD`.

Health score (weighted 0–100): Console 15%, Links 10%, Visual 10%, Functional 20%,
UX 15%, Performance 10%, Content 5%, Accessibility 15%. Deduct per finding:
critical −25 / high −15 / medium −8 / low −3.

Every bug needs evidence (screenshot or endpoint output). One atomic commit per fix:
`fix: <component> — <short desc>`. Re-verify after each fix. Revert on regression.

## Ship (pipeline)

Non-interactive: "ship" means run it through, output the PR/commit.

1. **Pre-flight** — on `main`? Abort (ship from a feature branch). Gather
   `git diff main...HEAD --stat`.
2. **Merge base** — `git fetch origin main && git merge origin/main --no-edit`.
3. **Tests / smoke** — run the app, exercise the changed paths. Fail → STOP.
4. **Review** — run the checklist below on the diff. Auto-fix trivial findings.
5. **Version + CHANGELOG** — bump `VERSION`, update `CHANGELOG.md` (see those files).
6. **Commit (bisectable)** — one logical change per commit; model+test together.
7. **Verify gate (IRON LAW)** — if code changed after testing, re-test with fresh
   output. "I'm confident" is not evidence.
8. **Push + PR** — never force-push. PR title starts with `v<VERSION>`.

Never skip: tests, review, fresh verification, secret scan before push.

## Review checklist (pre-merge)

- **P0 (block):** secret exposure, unvalidated input, authz gaps, data loss,
  broken core flow, untested logic.
- **P1 (fix):** correctness bugs, edge cases, error-handling gaps, perf regressions
  (N+1, unbounded loops).
- **P2 (should):** readability, dead code, stale comments, naming.
- **P3 (nit):** style.

Specific: LLM output is untrusted — never let agent/model output reach a shell/SQL/
exec sink unchecked. Side effects behind `if`/`try` must actually run. Tests must
assert *behavior*, not just `assert x is not None`.

## Completion status

End every task with one of: **DONE** (evidence) · **DONE_WITH_CONCERNS** · **BLOCKED**
(blocker + what was tried) · **NEEDS_CONTEXT** (what's missing).

## Security audit (CSO)

Infra-first. Daily: grep for hardcoded keys/tokens in git history + tree,
`pip-audit` on dependencies. Comprehensive: CI/CD, LLM attack surface (prompt
injection into tools), OWASP Top 10, STRIDE. Every report carries the disclaimer:
*"Automated heuristic audit, not a substitute for professional security review."*
