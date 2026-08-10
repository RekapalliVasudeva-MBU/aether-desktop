---
name: gstack-method
description: >-
  Engineering workflow discipline distilled from garrytan/gstack: plan -> review ->
  ship. Covers systematic debugging (root-cause-only fixes), QA test/fix/verify with
  health scoring, automated ship pipeline (merge/test/review/bump/CHANGELOG/PR),
  pre-landing code review checklist, turning vague intent into executable specs,
  security auditing, and product brainstorming. Use this as the operating manual
  for any non-trivial coding task.
version: 1.0.0
category: software-development
---

# gstack-method — Plan → Review → Ship

A portable distillation of the methodology in [garrytan/gstack](https://github.com/garrytan/gstack).
Stripped of the Claude/Codex-specific plumbing (its `bin/` CLIs, preamble hooks,
PreToolUse gates) and kept as a reusable operating manual for Hermes. The value is
the *discipline*, not the tooling.

## When to use this skill

- Debugging a bug or failure → use the **Investigate** protocol.
- Verifying a web app or feature works → use the **QA** protocol.
- Shipping a branch / opening a PR → use the **Ship** pipeline.
- Reviewing a diff before merge → use the **Review** checklist.
- Turning a vague idea into a ticket/issue → use the **Spec** protocol.
- Checking a codebase for security holes → use the **CSO** audit.
- Brainstorming product/scope → use the **Office Hours** framing.

## Core principles (apply to every protocol)

### Boil the Ocean
AI makes completeness cheap. Default to the *complete* thing: cover edge cases,
error paths, and tests. The only thing out of scope is genuinely unrelated work
(rewrites, multi-quarter migrations) — flag that as separate scope, never as an
excuse for a shortcut.

### Search Before Building
Before building anything unfamiliar, search first. Three layers:
1. **Tried and true** — don't reinvent; reuse existing patterns/libraries.
2. **New and popular** — scrutinize; hype is not a reason.
3. **First principles** — prize above all. When first-principles reasoning
   contradicts conventional wisdom, name it explicitly.

### User Sovereignty
You may suggest, scaffold, and auto-fill; you never silently decide for the user on
irreversible or taste-dependent calls (force-push, version MAJOR/MINOR bump, delete,
scope cuts). Present the tradeoff, recommend, then let them choose. Cross-model
agreement is a *recommendation*, not a decision.

### Completion Status Protocol
End every workflow with one status:
- **DONE** — completed with evidence.
- **DONE_WITH_CONCERNS** — completed, but list concerns.
- **BLOCKED** — cannot proceed; state blocker + what was tried.
- **NEEDS_CONTEXT** — missing info; state exactly what is needed.

If you hit 3 failed attempts, uncertain security-sensitive changes, or scope you
cannot verify: STOP and report `STATUS / REASON / ATTEMPTED / RECOMMENDATION`.

### Iron Law of Debugging
No fix without a root cause. Diagnose the *why* before editing. If you cannot
explain the mechanism of failure, you have not found the bug. Three+ failed fix
attempts on the same symptom → question the architecture, not the patch.

---

## INVESTIGATE — systematic debugging

Four phases. Do not skip to the fix.

1. **Investigate** — reproduce. Gather exact error, stack trace, inputs, env.
   Read the code path. Never mutate yet.
2. **Analyze** — form hypotheses ranked by likelihood. Trace data flow.
3. **Hypothesize** — state the root cause in one sentence you can test.
4. **Implement** — minimal fix that addresses the root cause, not the symptom.

Rules:
- Touch only files directly related to the root cause. No drive-by refactors.
- After a fix: re-run the repro. Fresh passing evidence required.
- If a fix makes things worse → revert immediately (`git revert HEAD`).
- >5 files touched without a clear root cause → stop and ask the user.
- Self-regulation: if looping on the same file/diagnostic, STOP and reassess.

**GUI/desktop pitfall (Iron Law applied to shipped apps):** when the user reports
"the app won't open" / "double-click does nothing", the repro is the REAL launch —
not a backend import, not `python desktop_app.py` in a terminal. A doc-only or
source edit to a repo CANNOT break an already-installed frozen `.exe` (the `.lnk`
points at `%LOCALAPPDATA%\<App>\App.exe`, a separate build). Diagnose the running
artifact live (process, port, window enumeration) before claiming a cause. The
concrete mutex/window-dead technique lives in `windows-app-launch-debug`.

## QA — test → fix → verify

Treat yourself as a QA engineer AND a bug-fix engineer. Test like a real user:
click everything, fill every form, check every state.

**Tiers** (which issues you fix):
- Quick: critical + high only.
- Standard (default): + medium.
- Exhaustive: + low/cosmetic.

**Diff-aware mode** (most common): when no URL given and on a feature branch,
auto-scope to the branch diff:
1. `git diff <base>...HEAD --name-only` + `git log <base>..HEAD --oneline`
2. Map changed files → affected pages/routes/endpoints.
3. Detect running app (localhost ports) or staging URL.
4. Test each affected page end-to-end; screenshot before/after interactions.
5. Cross-reference commit messages / PR description for *intent* — verify it does that.

**Health score** (weighted average, 0–100) — compute per category, deduct per finding:
- Console errors (15%): 0 err→100, 1–3→70, 4–10→40, 10+→10.
- Broken links (10%): each broken link −15.
- Visual (10%), Functional (20%), UX (15%), Performance (10%), Content (5%),
  Accessibility (15%): start 100, −25 critical / −15 high / −8 medium / −3 low.

**Rules:**
- Every issue needs a screenshot. Repro once to confirm (not a fluke).
- Write each issue to the report *as you find it* — don't batch.
- Never read source to "explain" a UI bug; test as a user. (Read source only in the fix loop.)
- One atomic commit per fix: `fix(qa): ISSUE-NNN — short desc`. Never bundle.
- Re-verify after each fix (before/after screenshot + console check).
- Revert on regression. Hard cap: 50 fixes; self-regulate via a WTF-likelihood heuristic
  (reverts, >3-file fixes, unrelated-file touches raise it; stop at >20%).

## SHIP — automated ship pipeline

Non-interactive by default: user said "ship" → run straight through, output PR URL.

1. **Pre-flight** — on base branch? Abort ("ship from a feature branch"). Gather
   `git diff <base>...HEAD --stat` + log. Uncommitted changes are always included.
2. **Merge base** — `git fetch origin <base> && git merge origin/<base> --no-edit`
   (auto-resolve trivial conflicts; STOP on complex/ambiguous).
3. **Tests** — run the suite. If prompt/eval files changed, run those too. Fail → STOP.
4. **Coverage audit** — check diff coverage; generate missing tests within threshold.
5. **Plan completion** — if a plan file exists, verify all items DONE; flag scope drift.
6. **Pre-landing review** — run the Review checklist (below) on the diff. Auto-fix
   trivial findings (dead code, N+1, stale comments). ASK items → stop for user.
7. **Adversarial review** — challenge your own plan/diff; capture learnings.
8. **Version bump** — auto MICRO/PATCH from diff scale; ASK only for MINOR (feature
   signal / 500+ lines) or MAJOR (breaking). Keep a 4-part `MAJOR.MINOR.PATCH.MICRO`
   or your repo's scheme; write VERSION + package manifest together.
9. **CHANGELOG** — auto-generate entry from the diff (group by type: feat/fix/chore).
10. **TODOS.md** — conservatively mark completed items; never delete.
11. **Commit (bisectable)** — one logical change per commit; model+test together,
    controller+view+test together, migrations standalone, VERSION+CHANGELOG last.
12. **Verification gate (IRON LAW)** — if code changed after the test run, re-run
    tests with *fresh* output. "I'm confident" is not evidence. Fail → STOP, do not push.
13. **Push** — credential pre-push guard (scan for secrets/keys/tokens); never force-push.
14. **PR/MR** — title starts with `v<NEW_VERSION>`; body includes review summary,
    coverage %, plan completion, QA delta. Idempotent: update existing PR body, don't
    duplicate.

**Never skip:** tests, pre-landing review, fresh verification before push, secret scan.

## REVIEW — pre-landing code review checklist

Run on the diff before merge. Priorities (gate order):
- **P0 (block merge):** security (SQL injection, unauthenticated access, secret
  exposure, unvalidated input), data loss, broken core flow, missing tests on logic.
- **P1 (fix before merge):** correctness bugs, edge cases, error handling gaps,
  perf regressions (N+1, unbounded loops), tests that don't assert behavior.
- **P2 (should fix):** readability, dead code, stale comments, naming, duplication.
- **P3 (nit):** style, formatting.

Specific checks:
- **LLM trust boundary** — never let model output reach a shell/SQL/exec sink
  unchecked; treat LLM output as untrusted user input.
- **Conditional side effects** — side effects behind `if`/`try` that can silently
  no-op; verify they actually run.
- **Defense in depth** — missing null/empty checks at boundaries; authz checked on
  every path, not just the happy one.
- **Tests assert behavior** — `expect(x).toBeDefined()` is not a test. Test what the
  code *does*, including both branches of every conditional.

Report format: severity, file:line, the problem, the concrete fix, evidence.

## SPEC — vague intent → executable spec

Five phases. Output a backlog-ready issue/ticket.
1. **Clarify** — extract the real goal. Ask (don't assume) on ambiguous scope,
   success criteria, constraints, non-goals.
2. **Context** — search existing code/patterns (Search Before Building). Note what
   exists, what to reuse.
3. **Decompose** — break into independent, testable work items. Each item = one
   logical change with an acceptance criterion.
4. **Risks** — call out unknowns, dependencies, rollback/blast radius.
5. **Write** — produce the spec: problem, proposed approach, itemized tasks with
   Done definitions, test plan, open questions. Keep it executable, not aspirational.

## CSO — security audit

Infrastructure-first, two modes:
- **Daily** (fast, 8/10 confidence bar): secrets archaeology (grep for hardcoded
  keys/tokens in git history + working tree), dependency supply-chain (`pip-audit` /
  `npm audit` / `cargo audit`), obvious misconfigs.
- **Comprehensive** (2/10 confidence bar — i.e. be thorough): + CI/CD pipeline
  security, LLM/AI attack surface (prompt injection into tools, unguarded eval),
  OWASP Top 10, STRIDE (Spoofing, Tampering, Repudiation, Information disclosure,
  Denial of service, Elevation of privilege).

Every report MUST include a disclaimer: *"This is an automated heuristic audit, not a
substitute for a professional security review."* Findings: severity, location,
impact, concrete remediation.

## OFFICE HOURS — product / scope brainstorm

Two modes:
- **Brainstorm** — pressure-test the idea. Who is the user? What pain? What's the
  smallest thing that delivers value? What already exists (Search Before Building)?
- **Decide** — when scope is fuzzy, present 2–3 options with tradeoffs and a
  recommendation. Use the *Completeness* framing: 10 = complete, 7 = happy path,
  3 = shortcut. Name the stakes. Let the user choose on taste/scope calls.

---

## Voice (how to write findings)

- Lead with the point. Name files, functions, line numbers, commands, outputs.
- Tie choices to user outcomes: what the user sees, loses, waits for.
- Direct about quality. Fix the whole thing, not the demo path.
- Builder-to-builder, not consultant-to-client. No hype, no filler.
- No credo words (delve, crucial, robust, comprehensive, nuanced, multifaceted,
  pivotal, tapestry, underscore, foster, showcase).

## Porting notes (gstack → Hermes)

- gstack's `bin/gstack-*` CLIs, preamble hooks, and PreToolUse freeze gates are
  Claude/Codex-specific. Replace with: Hermes `terminal` for git, `read_file`/
  `search_files` for code, `todo` for the task list, `skill_manage` to update this
  skill, and `clarify` for the AskUserQuestion-equivalent decision gates.
- The `AskUserQuestion` decision-brief format (ELI10 + Completeness score +
  Recommendation + (recommended) label + Net line) maps directly to the `clarify`
  tool's multiple-choice shape.
- gstack's `~/.gstack/projects/<slug>/*.jsonl` memory → Hermes `memory` /
  `fact_store` for cross-session learnings, and `skill_manage` patches for pitfalls.
- Version scheme, CHANGELOG format, and TODOS.md structure are repo-convention;
  adapt to the target repo, don't impose gstack's 4-digit scheme blindly.
- **Step-by-step porting technique** (extraction order, what to skip, construct map,
  how to apply to a target repo) → `references/porting-agent-config-repos.md`.
