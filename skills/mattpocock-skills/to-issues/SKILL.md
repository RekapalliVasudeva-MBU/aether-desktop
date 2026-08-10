---
name: to-issues
description: Break a plan, spec, or PRD into independently-grabbable GitHub issues using tracer-bullet vertical slices. Use when user wants to convert a plan into issues, create implementation tickets, or break down work into issues.
---

# To Issues

Break a plan into independently-grabbable issues using vertical slices (tracer bullets).

## Process

### 1. Gather Context
Work from conversation context. If user passes an issue reference, fetch and read it fully.

### 2. Explore the Codebase
Understand current state. Use project's domain glossary vocabulary. Respect ADRs in the area.

### 3. Draft Vertical Slices
Each slice is a thin vertical slice cutting through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
- Mark slices as HITL (needs human interaction) or AFK (can be done autonomously)

### 4. Quiz the User
Present proposed breakdown as numbered list. For each slice show: Title, Type (HITL/AFK), Blocked by, User stories covered.

Ask: granularity right? dependencies correct? merge/split needed?

### 5. Publish Issues
For each approved slice, create a GitHub issue using this template:

```
## Parent
[Reference to parent issue if applicable]

## What to build
Concise description of end-to-end behavior. Avoid specific file paths.

## Acceptance criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Blocked by
- [Blocking ticket reference] or "None - can start immediately"
```

Publish in dependency order (blockers first).
