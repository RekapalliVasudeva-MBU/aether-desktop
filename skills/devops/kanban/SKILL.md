---
name: kanban
description: "Multi-agent Kanban work queue: orchestrator decomposition playbook and worker lifecycle/pitfalls. Use when decomposing work into Kanban tasks for multi-profile routing, or when working as a Kanban worker. Covers: task graph design, dependency linking, worker lifecycle (orient→work→heartbeat→complete), goal-mode persistent workers."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, multi-agent, orchestration, work-queue, collaboration]
---

# Kanban — Multi-Agent Work Queue

Durable SQLite board for multi-profile/multi-worker collaboration.

## Two Roles

| Role | Skill Focus |
|------|-------------|
| **Orchestrator** | §1 — Decompose work, create tasks, route to profiles |
| **Worker** | §2 — Claim tasks, do work, hand off |

---

## §1 — Orchestrator (Decomposition Playbook)

### Step 0: Discover Profiles

Before creating tasks, discover available profiles:
- `hermes profile list` or ask the user
- Never invent profile names — unknown assignees silently fail

### When to Use Kanban

Create Kanban tasks when: multiple specialists needed, work should survive restarts, user might interject, parallel work possible, review/iteration expected, audit trail matters.

### Decomposition Process

1. **Understand the goal** — ask clarifying questions
2. **Sketch the task graph** — extract lanes, map to profiles, identify dependencies
3. **Align with user** — show the graph before creating cards
4. **Create tasks** — `kanban_create` with `parents=[...]` for dependencies

### Task Graph Examples

**Fan-out + fan-in:**
```
T1 (research A) ──┐
                   ├── T3 (synthesize) ── T4 (draft)
T2 (research B) ──┘
```

**Pipeline:**
```
T1 (plan) → T2 (implement) → T3 (review)
```

### Parent Links

Children with unfinished parents start in `todo`. Dispatcher promotes to `ready` only after all parents are `done`.

### Goal-Mode Workers

For long-running tasks, pass `goal_mode=True` wraps worker in a Ralph-style loop:
- Judge re-checks after each turn
- Worker continues in same session if not done
- Budget exhausted → blocked for human review

---

## §2 — Worker (Lifecycle & Pitfalls)

### Workspace Kinds

`scratch` (fresh tmp), `dir:<path>` (shared), `worktree` (git worktree).

### Tenant Isolation

If `HERMES_TENANT` is set, prefix memory entries with tenant name.

### Complete Handoff Pattern

```python
kanban_complete(
    summary="shipped feature — 14 tests pass",
    metadata={
        "changed_files": ["feature.py", "tests/test_feature.py"],
        "tests_run": 14,
        "tests_passed": 14,
    },
)
```

### Review-Required Pattern

```python
kanban_comment(body="review-required handoff:\n" + json.dumps({...}, indent=2))
kanban_block(reason="review-required: description — needs eyes before merging")
```

### Claiming Created Cards

```python
c1 = kanban_create(title="fix SQL injection", assignee="security-worker")
kanban_complete(summary="...", created_cards=[c1["task_id"]])
```

### Heartbeats

Every few minutes: `kanban_heartbeat(notes="scanned 1.2M/2.4M rows")`.

### Retry Diagnostics

Check `kanban_show` runs for previous outcomes: `timed_out`, `crashed`, `spawn_failed`, `blocked`.

### DON'T

- Call `delegate_task` as substitute for `kanban_create`
- Call `clarify` (headless — will timeout)
- Modify files outside workspace unless told to
- Create follow-up tasks assigned to yourself
- Complete unfinished tasks — block instead
