# Porting an agent-config repo (gstack-style) into a Hermes skill

Reusable technique from distilling `garrytan/gstack` into the `gstack-method` skill.
Applies whenever the user points at a Claude Code / Codex / Cursor agent-config repo
and says "extract the methodology" or "add this to our workflow."

## Why this exists

These repos (gstack, etc.) are valuable for their *discipline* (workflow checklists,
voice rules, decision protocols), not their tooling. 95% of the file is
Claude/Codex-specific plumbing that is dead weight in Hermes. Port the methodology,
drop the plumbing.

## Extraction order (what to read)

Read via the `mcp__github__get_file_contents` tool (owner/repo/path). Big skill files
truncate — read the parts you need; the frontmatter + the workflow body are what matter.

1. `README.md` — repo purpose, skill list, routing map.
2. `SKILL.md` (top-level) — what the config is, how skills are invoked.
3. `AGENTS.md` — agent constraints, structure notes.
4. `ETHOS.md` — the philosophy preamble auto-injected into every skill (e.g. gstack's
   "Boil the Ocean", "Search Before Building", "Build for Yourself"). This is the
   highest-value extract — it's the cross-cutting principle layer.
5. Each `*/SKILL.md` under the repo — the actual workflows (investigate, qa, ship,
   review, spec, cso, office-hours, plan-* , design-*). These become the protocol
   sections.

**Skip / ignore:**
- The `## Preamble (run first)` bash block in every skill — it's gstack's
  telemetry/update/feature-detection harness. Pure Claude plumbing. Do not port.
- `bin/gstack-*` CLIs, `PreToolUse`/`PostToolUse` hooks, `scripts/question-registry.ts`,
  `gstack-config` calls. Platform-specific. Drop.
- `AGENTS.md` "Skill routing" injection and first-run detection — session UX, not method.

## Distillation rules

- **Consolidate, don't mirror.** gstack ships ~12 separate skill dirs. Port them as
  *sections of one class-level skill* (`gstack-method`), not 12 narrow skills. The
  user reuses the whole workflow; a flat list of one-shot skills is harder to load.
- **Keep the checklists, drop the automation.** The QA health-score rubric, the
  ship-pipeline step list, the P0–P3 review priorities, the Iron Law of debugging —
  these are pure method. The `gstack-version-bump` CLI that executes step 8 is not.
- **Adapt conventions, don't impose.** gstack's 4-part `MAJOR.MINOR.PATCH.MICRO`
  version, its TODOS.md shape, its CHANGELOG format are *its* repo's convention. When
  you add the structure to a *target* repo, match that repo's existing scheme
  (Aether used 3-part `MAJOR.MINOR.PATCH` and already had commit history to seed
  CHANGELOG/TODOS from).
- **Map constructs to Hermes equivalents** (see table below). Never tell the user
  "I can't" when the equivalent tool exists.

## Construct map (Claude/Codex → Hermes)

| gstack construct | Hermes equivalent |
|---|---|
| `AskUserQuestion` decision brief (ELI10 + Completeness + Recommendation + Net) | `clarify` tool (multiple-choice; one open-ended option) |
| `bin/gstack-*` CLIs (version-bump, decision-log, learnings) | `terminal` for git/version; `memory`/`fact_store` for learnings; `skill_manage` to patch the skill |
| `~/.gstack/projects/<slug>/*.jsonl` cross-session memory | Hermes `memory` tool + `fact_store` |
| PreToolUse freeze hooks on Edit/Write | (not needed — Hermes has no equivalent gating; enforce via the Iron Law in the skill body) |
| `todo` list in skill | Hermes `todo` tool |
| `Bash`/`Read`/`Grep`/`Glob` | Hermes `terminal` / `read_file` / `search_files` |
| `codex exec` / `codex review` subagents | Hermes `delegate_task` (leaf) |
| Preamble telemetry / update-check | drop entirely |

## Applying it to a target repo

When the user says "add this structure to our project":
1. **Inspect first, never assume.** Resolve the project path, read its real layout,
   git status, remote, recent log. Don't write blind.
2. **The methodology is an AI-agent discipline — it does NOT execute inside the
   target app's runtime code.** Realistic deliverables are **doc/process artifacts**
   (ENGINEERING.md, AGENTS.md, TODOS.md, CHANGELOG.md, VERSION) — not runtime features.
   State this honestly; offer VERSION/CHANGELOG automation or skills.py wiring as
   separate, explicit options rather than assuming.
3. **Scope the commit.** `git add` only the files you created/edited. Never
   `git add -A` (ship-pipeline rule). Leave build artifacts / logs untracked.
4. **Respect repo-visibility rules.** If the user's memory forbids public repos,
   flag a public remote but do NOT change its visibility — user handles that switch.
5. **Commit + push** with a descriptive message; reference the workflow in the body.

## Pitfalls hit this session (and avoided)

- gstack SKILL.md files are ~80–130 KB; the MCP tool truncates at ~104–137 K chars.
  You still get the frontmatter + most of the workflow body. Don't re-fetch expecting
  the full file — read the section you need and move on.
- The `clarify` tool can return with no `user_response` (UI dismissed / no pick).
  Don't block forever — make a reasonable default, do the safe reversible subset
  (docs-only), and offer the heavier options as a follow-up. Never silently do the
  destructive/irreversible part.
- Aether's `chromadb_pkg/` is vendored third-party — note it as off-limits in the
  generated AGENTS.md so future agents don't edit it.
