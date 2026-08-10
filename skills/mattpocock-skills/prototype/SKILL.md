---
name: prototype
description: Build a throwaway prototype to flesh out a design before committing to it. Use when user wants to prototype, sanity-check a data model or state machine, mock up a UI, explore design options, or says "prototype this", "let me play with it", "try a few designs".
---

# Prototype

A prototype is **throwaway code that answers a question**. The question decides the shape.

## Pick a Branch

- **"Does this logic / state model feel right?"** → Build a tiny interactive terminal app that pushes the state machine through hard-to-reason-about cases.
- **"What should this look like?"** → Generate several radically different UI variations on a single route, switchable via URL search param.

If ambiguous, default to whichever branch better matches the surrounding code (backend → logic, frontend → UI).

## Rules

1. **Throwaway from day one.** Name it clearly as a prototype. Place it close to where it will actually be used.
2. **One command to run.** Use the project's existing task runner.
3. **No persistence by default.** State lives in memory.
4. **Skip the polish.** No tests, no error handling beyond runnable, no abstractions.
5. **Surface the state.** After every action, print/render the full relevant state.
6. **Delete or absorb when done.** Don't leave it rotting in the repo.

## When Done

Capture the _answer_ somewhere durable (commit message, ADR, issue, or NOTES.md) along with the question it was answering.
