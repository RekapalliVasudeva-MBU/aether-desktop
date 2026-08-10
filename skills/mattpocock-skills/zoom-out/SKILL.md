---
name: zoom-out
description: Zoom out and give broader context or a higher-level perspective on an unfamiliar section of code. Use when user is unfamiliar with a section of code, needs to understand how it fits into the bigger picture, or says "zoom out", "give me context", "how does this fit".
---

# Zoom Out

The user doesn't know this area of code well. Go up a layer of abstraction.

Give a map of all relevant modules and callers, using the project's domain glossary vocabulary.

## What to Provide

1. **High-level overview** — What does this module/area do in 2-3 sentences?
2. **Module map** — What are the key modules/files and how do they relate?
3. **Data flow** — How does data flow through this area?
4. **Key abstractions** — What are the main interfaces/concepts?
5. **Entry points** — Where does execution start when this area is triggered?
6. **Dependencies** — What does this area depend on? What depends on it?

Use the project's domain language. Don't just list files — explain the architecture.
