---
name: tdd
description: Test-driven development with red-green-refactor loop. Use when user wants to build features or fix bugs using TDD, mentions "red-green-refactor", wants integration tests, or asks for test-first development.
---

# Test-Driven Development

## Philosophy

**Core principle**: Tests verify behavior through public interfaces, not implementation details.

**Good tests** are integration-style: exercise real code paths through public APIs. Describe _what_ the system does, not _how_. Survive refactors.

**Bad tests** are coupled to implementation: mock internal collaborators, test private methods, verify through external means. Break when behavior hasn't changed.

## Anti-Pattern: Horizontal Slices

**DO NOT write all tests first, then all implementation.** This produces crap tests that test imagined behavior.

**Correct approach**: Vertical slices via tracer bullets. One test → one implementation → repeat.

```
WRONG:  RED: test1,test2,test3 → GREEN: impl1,impl2,impl3
RIGHT:  RED→GREEN: test1→impl1 → RED→GREEN: test2→impl2 → ...
```

## Workflow

### 1. Planning
- Confirm interface changes needed
- Confirm which behaviors to test (prioritize)
- Identify opportunities for deep modules (small interface, deep implementation)
- Get user approval on the plan

### 2. Tracer Bullet
Write ONE test that confirms ONE thing:
```
RED:   Write test for first behavior → test fails
GREEN: Write minimal code to pass → test passes
```

### 3. Incremental Loop
For each remaining behavior:
```
RED:   Write next test → fails
GREEN: Minimal code to pass → passes
```
Rules: One test at a time. Only enough code to pass current test. Don't anticipate future tests.

### 4. Refactor
After all tests pass: extract duplication, deepen modules, apply SOLID principles. Run tests after each refactor step. **Never refactor while RED.**

## Checklist Per Cycle
- [ ] Test describes behavior, not implementation
- [ ] Test uses public interface only
- [ ] Test would survive internal refactor
- [ ] Code is minimal for this test
- [ ] No speculative features added
