---
name: code-quality
description: "Code quality workflows: test-driven development, pre-commit verification, and parallel code review. Use when writing tests first (TDD), verifying code before committing (security scan + lint + review), or running parallel 3-agent code cleanup. Covers: RED-GREEN-REFACTOR, pre-commit security/quality gates, simplify (parallel review)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [code-quality, tdd, testing, code-review, security, pre-commit, simplify]
---

# Code Quality

Test-driven development, pre-commit verification, and parallel code review.

## When to Use

- Writing new features or bug fixes (TDD)
- Before committing code (verification)
- Cleaning up recent changes (parallel review)

---

## §1 — Test-Driven Development (TDD)

**Iron law:** NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.

### Red-Green-Refactor Cycle

1. **RED** — Write one minimal failing test
2. **Verify RED** — Run test, confirm it fails for expected reason
3. **GREEN** — Write simplest code to pass (hardcode OK)
4. **Verify GREEN** — Run test + full suite
5. **REFACTOR** — Clean up, keep tests green
6. **Repeat** — Next failing test

### Good Test

```python
def test_retries_failed_operations_3_times():
    attempts = 0
    def operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3: raise Exception('fail')
        return 'success'
    result = retry_operation(operation)
    assert result == 'success'
    assert attempts == 3
```

### Verification Checklist

- [ ] Every new function/method has a test
- [ ] Watched each test fail before implementing
- [ ] All tests pass, no regressions

---

## §2 — Pre-Commit Verification

Automated pipeline before code lands.

### Steps

1. **Get diff:** `git diff --cached` (or `git diff`)
2. **Security scan:** Check for hardcoded secrets, shell injection, eval/exec, SQL injection, pickle.loads
3. **Baseline tests:** Run tests before/after to detect regressions
4. **Lint:** ruff/eslint/mypy as appropriate
5. **Self-review checklist:** Input validation, error handling, no debug prints
6. **Independent reviewer:** `delegate_task` with diff + scan results
7. **Auto-fix loop:** Max 2 fix-and-reverify cycles
8. **Commit:** `git add -A && git commit -m "[verified] <description>"`

### Security Patterns to Flag

```python
# SQL injection
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
# Fix: cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# Shell injection
os.system(f"ls {user_id}")
# Fix: subprocess.run(["ls", user_input], check=True)
```

---

## §3 — Simplify (Parallel 3-Agent Cleanup)

Review recent code changes with three focused reviewers in parallel.

### Three Reviewers

1. **Code Reuse** — Duplicates existing functionality?
2. **Code Quality** — Redundant state, parameter sprawl, copy-paste?
3. **Efficiency** — Unnecessary work, missed concurrency, hot-path bloat?

### Process

1. Capture diff: `git diff` (or `git diff HEAD~1`)
2. Launch 3 reviewers via `delegate_task` batch mode
3. Aggregate findings, dedup, resolve conflicts
4. Apply fixes with `patch`/`write_file`
5. Verify — run targeted tests + linter

### Rules

- Give WHOLE diff to each reviewer
- Only flag things that materially improve code
- Apply ≠ rewrite — keep edits scoped to diff
- Max 3 reviewers (more = more cost, not better coverage)
