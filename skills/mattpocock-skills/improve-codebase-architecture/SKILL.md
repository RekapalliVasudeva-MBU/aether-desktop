---
name: improve-codebase-architecture
description: Find deepening opportunities in a codebase. Use when user wants to improve architecture, find refactoring opportunities, consolidate tightly-coupled modules, or make a codebase more testable and AI-navigable.
---

# Improve Codebase Architecture

Surface architectural friction and propose **deepening opportunities** — refactors that turn shallow modules into deep ones.

## Key Concepts

- **Module** — anything with an interface and implementation
- **Interface** — everything a caller must know to use the module
- **Depth** — leverage at the interface: lots of behavior behind a small interface
- **Seam** — where an interface lives; behavior can be altered without editing in place
- **Adapter** — concrete thing satisfying an interface at a seam
- **Locality** — change, bugs, knowledge concentrated in one place

**Deletion test**: Imagine deleting the module. If complexity vanishes, it was a pass-through. If complexity reappears across N callers, it was earning its keep.

## Process

### 1. Explore
Read domain glossary and ADRs first. Walk the codebase organically. Note friction:
- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow** — interface nearly as complex as implementation?
- Where do tightly-coupled modules leak across seams?
- Which parts are untested or hard to test?

### 2. Present Candidates
Numbered list of deepening opportunities. For each:
- **Files** — which files/modules involved
- **Problem** — why current architecture causes friction
- **Solution** — what would change
- **Benefits** — locality, leverage, testability

Use CONTEXT.md vocabulary. Don't propose interfaces yet. Ask user which to explore.

### 3. Grilling Loop
Walk the design tree: constraints, dependencies, shape of deepened module, what sits behind the seam.

Update CONTEXT.md inline when naming new concepts. Offer ADRs when load-bearing reasons are given.
