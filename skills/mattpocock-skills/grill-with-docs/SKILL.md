---
name: grill-with-docs
description: Grilling session that challenges the plan against the existing domain model, sharpens terminology, and updates documentation (CONTEXT.md, ADRs) inline as decisions crystallise. Use when user wants to stress-test a plan against their project's language and documented decisions, or when starting a complex project with domain complexity.
---

# Grill With Docs

Interview the user relentlessly about every aspect of the plan until reaching shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one.

Ask questions one at a time, waiting for feedback.

## Domain Awareness

During codebase exploration, look for existing documentation:

- `CONTEXT.md` — shared domain glossary at repo root
- `docs/adr/` — architecture decision records
- If `CONTEXT-MAP.md` exists, the repo has multiple contexts

Create files lazily — only when you have something to write.

## During the Session

### Challenge against the glossary
When the user uses a term that conflicts with existing language in `CONTEXT.md`, call it out immediately: "Your glossary defines 'cancellation' as X, but you seem to mean Y — which is it?"

### Sharpen fuzzy language
Propose precise canonical terms for vague or overloaded words.

### Discuss concrete scenarios
Stress-test domain relationships with specific edge-case scenarios.

### Cross-reference with code
Check whether the code agrees with what the user states. Surface contradictions.

### Update CONTEXT.md inline
When a term is resolved, update `CONTEXT.md` right there. Only include terms meaningful to domain experts.

### Offer ADRs sparingly
Only create an ADR when ALL three are true:
1. **Hard to reverse** — meaningful cost to change later
2. **Surprising without context** — future readers will wonder why
3. **Real trade-off** — genuine alternatives were considered

## When to Use

- Starting a complex project with lots of domain jargon
- When existing documentation should inform the design
- Before major architectural decisions
