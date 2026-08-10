---
name: triage
description: Triage issues through a state machine driven by triage roles. Use when user wants to triage issues, review incoming bugs or feature requests, prepare issues for an agent, or manage issue workflow.
---

# Triage

Move issues through a state machine of triage roles.

## Roles

**Category roles:** `bug` (something broken), `enhancement` (new feature)

**State roles:** `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`

Every triaged issue carries exactly one category + one state.

## State Flow

```
unlabeled → needs-triage → needs-info → needs-triage (when reporter replies)
                          → ready-for-agent
                          → ready-for-human
                          → wontfix
```

## Show What Needs Attention

Present three buckets, oldest first:
1. **Unlabeled** — never triaged
2. **needs-triage** — evaluation in progress
3. **needs-info with reporter activity** — needs re-evaluation

## Triage a Specific Issue

1. **Gather context** — Read full issue, comments, labels. Parse prior triage notes. Explore codebase.
2. **Recommend** — Category + state with reasoning. Wait for direction.
3. **Reproduce (bugs)** — Attempt reproduction. Report result.
4. **Grill (if needed)** — Run grilling session for fleshing out.
5. **Apply outcome:**
   - `ready-for-agent` → post agent brief
   - `ready-for-human` → post brief noting why it can't be delegated
   - `needs-info` → post triage notes
   - `wontfix` → polite explanation, close

## Quick State Override

If user says "move #42 to ready-for-agent", trust them and apply directly. Confirm what you're about to do, then act.

## Needs-Info Template

```markdown
## Triage Notes

**What we've established so far:**
- point 1
- point 2

**What we still need from you (@reporter):**
- question 1
- question 2
```
