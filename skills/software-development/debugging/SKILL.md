---
name: debugging
description: "Systematic root cause debugging and Node.js inspect debugging. Use when debugging code — finding root causes before fixing bugs, setting breakpoints in Node.js via --inspect + CDP, or following a structured 4-phase debugging process. Covers: systematic-debugging (understand-before-fixing), Node.js inspect CLI, Chrome DevTools Protocol, heap/CPU profiling."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, root-cause, breakpoints, nodejs, CDP, inspect, troubleshooting]
---

# Debugging

Systematic root cause debugging + Node.js inspect debugging.

## When to Use

- Test failures, production bugs, unexpected behavior
- Need breakpoint-driven debugging in Node.js
- Performance profiling (heap snapshots, CPU profiles)
- Following a structured debug process (understand before fixing)

---

## §1 — Systematic Debugging (4-Phase)

**Iron law:** NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.

### Phase 1: Root Cause Investigation

1. **Read error messages carefully** — don't skip past them
2. **Reproduce consistently** — exact steps, every time?
3. **Check recent changes** — `git log --oneline -10`, `git diff`
4. **Gather evidence** — log data in/out at each component boundary
5. **Trace data flow** — where does the bad value originate?

**Completion checklist:**
- [ ] Error messages fully read
- [ ] Issue reproduced consistently
- [ ] Recent changes reviewed
- [ ] Problem isolated to specific component

### Phase 2: Pattern Analysis

1. Find working examples in the same codebase
2. Compare against references
3. Identify differences between working and broken
4. Understand dependencies

### Phase 3: Hypothesis and Testing

1. Form single hypothesis: "I think X is the root cause because Y"
2. Test minimally — one variable at a time
3. Verify before continuing
4. If ≥3 fixes failed → question the architecture

### Phase 4: Implementation

1. Create failing test case first
2. Implement single fix for root cause
3. Verify fix — run full test suite
4. If fix doesn't work → new hypothesis (not more patches)

### Red Flags — STOP and Follow Process

- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- Proposing solutions before tracing data flow
- ≥3 failed fixes → question architecture, don't fix again

---

## §2 — Node.js Inspect Debugging

Two tools:
- **`node inspect`** — built-in, zero install, CLI REPL
- **CDP via `chrome-remote-interface`** — scriptable automation

### Launch

```bash
node inspect script.js                  # pause on first line
node --inspect script.js               # run, listen on :9229
node --inspect-brk script.js           # pause on first line
node --inspect-brk -p <pid>            # attach to running process
```

### node inspect REPL Commands

| Command | Action |
|---------|--------|
| `c` / `cont` | continue |
| `n` / `next` | step over |
| `s` / `step` | step into |
| `o` / `out` | step out |
| `sb('file.js', 42)` | set breakpoint |
| `bt` | backtrace |
| `list(5)` | show source |
| `repl` | drop into REPL in current scope |
| `exec expr` | evaluate expression |
| `.exit` | quit |

In `repl` sub-mode: access locals/closure variables. Ctrl+C exits back to `debug>`.

### Attaching to Running Process

```bash
kill -SIGUSR1 <pid>          # enable inspector
node inspect -p <pid>        # attach
```

### TypeScript (tsx)

```bash
node --inspect-brk --import tsx script.ts
```

### Automation (CDP)

```bash
npm i -g chrome-remote-interface
node --inspect-brk=9229 target.js &
node /tmp/cdp-debug.js        # automation script
```

### CPU Profiles & Heap Snapshots

```javascript
// CPU profile
await client.Profiler.start();
await new Promise(r => setTimeout(r, 5000));
const { profile } = await client.Profiler.stop();
require('fs').writeFileSync('/tmp/cpu.cpuprofile', JSON.stringify(profile));

// Heap snapshot
await client.HeapProfiler.takeHeapSnapshot({ reportProgress: false });
```

### Common Pitfalls

- **Wrong line numbers in TS source — break in `dist/*.js` or enable sourcemaps**
- **`--inspect` vs `--inspect-brk` — use `-brk` when you need initial breakpoints**
- **Port collisions — default 9229, use `--inspect=0` for random**
- **`--inspect` on parent doesn't inspect children — use `NODE_OPTIONS='--inspect-brk'`**
- **Ctrl+C out of `node inspect` while paused keeps target paused — `cont` first**
- **Eclipse build producing empty `bin/`** — check `.classpath` JRE version and `.settings/org.eclipse.jdt.core.prefs` `source`/`targetPlatform`/`compliance` must match the available JRE. See `references/eclipse-java-silent-failure.md` for full diagnostic steps and fix template.
- **Duplicate keys in `.prefs` files** — Java `.prefs` use last-wins semantics; a trailing duplicate overrides your fix. Grep the entire file for all occurrences.
- **Duplicate keys in `.prefs` files — Java `.prefs` use last-wins semantics; a trailing duplicate `source=26` after your fix `source=21` silently overrides the fix. Always grep for all occurrences.**
