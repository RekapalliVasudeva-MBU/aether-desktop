---
name: clarify-user-message
description: Handle incomplete, ambiguous, or unclear user requests by asking targeted clarifying questions before proceeding.
tags: [communication, workflow]
related_skills: [caveman, diagnose]
---

# Clarify User Message

When user message is incomplete, ambiguous, or lacks necessary context.

Signals to Trigger

- Message cuts off mid-sentence ("hi can u tell me now i have recharged\u2026")
- Missing key details (what, where, when, why)
- Contradictory statements
- Vague requests ("handle this", "do something")
- Multiple possible interpretations
- User corrections about agent capabilities ("you cannot access this", "you're hallucinating", "you're in a restricted environment")
- User frustration about scope limitations ("you say you can X but you can't", "you're lying about your access")
- Agent infrastructure reality checks (user correcting agent's stated constraints)

## Pattern

1. **Acknowledge** the incomplete message
2. **Ask ONE specific question** to clarify the missing piece
3. **Wait for response** before proceeding
4. **If no response**, offer limited options or default assumption

## Do NOT

- Assume intent and proceed with wrong interpretation
- Ask multiple clarifying questions at once
- Proceed with partial information when critical details missing
- Ask clarifying questions when user explicitly states they want you to "figure it out" or take decisive action
- Continue questioning when user shows frustration with lack of progress (phrases like "just do it", "figure it out yourself", "no need to specify")
- Continue questioning when user shows frustration with lack of progress (phrases like "just do it", "figure it out yourself", "no need to specify")

## Example

Wrong: "I'll check your config and see what happened with the recharge."

Right: "Your message cut off at 'recharged'. Can you complete it? Did you recharge your OpenRouter credits, or something else?"