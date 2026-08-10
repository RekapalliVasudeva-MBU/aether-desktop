---
name: to-prd
description: Turn the current conversation context into a PRD and publish it to the project issue tracker. Use when user wants to create a PRD from the current context, formalize a feature discussion, or document requirements.
---

# To PRD

Takes the current conversation context and codebase understanding and produces a PRD. Do NOT interview the user — synthesize what you already know.

## Process

1. Explore the repo to understand current state if not already done. Use domain glossary vocabulary.

2. Sketch major modules needed. Look for opportunities to extract deep modules (small interface, deep implementation).

3. Write the PRD using this template:

```
## Problem Statement
The problem from the user's perspective.

## Solution
The solution from the user's perspective.

## User Stories
1. As an <actor>, I want a <feature>, so that <benefit>
2. ...

## Implementation Decisions
- Modules to build/modify
- Interface changes
- Technical clarifications
- Architectural decisions
- Schema changes, API contracts

Do NOT include specific file paths. Exception: prototype snippets that encode decisions precisely.

## Testing Decisions
- What makes a good test (external behavior, not implementation)
- Which modules to test
- Prior art for tests

## Out of Scope
What's explicitly not included.

## Further Notes
Any additional context.
```
