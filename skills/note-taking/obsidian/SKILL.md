---
name: obsidian
description: Read, search, create, and edit notes in the Obsidian vault.
platforms: [linux, macos, windows]
---

# Obsidian Vault

Use this skill for filesystem-first Obsidian vault work: reading notes, listing notes, searching note files, creating notes, appending content, and adding wikilinks.

## Vault path

Use a known or resolved vault path before calling file tools.

The documented vault-path convention is the `OBSIDIAN_VAULT_PATH` environment variable, for example from `~/.hermes/.env` or `~/.hermes/config.yaml` (under `env:` section). If it is unset, try these fallbacks in order:
1. `~/Documents/Obsidian-Vault` (hyphen — common on Windows)
2. `~/Documents/Obsidian Vault` (space — default Obsidian naming)
3. Prompt the user if neither exists

**Windows:** On this platform, vault names commonly use hyphens instead of spaces. Always check `Documents/` for both variants.

File tools do not expand shell variables. Do not pass paths containing `$OBSIDIAN_VAULT_PATH` to `read_file`, `write_file`, `patch`, or `search_files`; resolve the vault path first and pass a concrete absolute path. Vault paths may contain spaces, which is another reason to prefer file tools over shell commands.

If the vault path is unknown, `terminal` is acceptable for resolving `OBSIDIAN_VAULT_PATH` or checking whether the fallback path exists. Once the path is known, switch back to file tools.

**Set the env var** so future sessions find it automatically:
```
hermes config set env.OBSIDIAN_VAULT_PATH "C:\Users\<user>\Documents\Obsidian-Vault"
```

## Read a note

Use `read_file` with the resolved absolute path to the note. Prefer this over `cat` because it provides line numbers and pagination.

## List notes

Use `search_files` with `target: "files"` and the resolved vault path. Prefer this over `find` or `ls`.

- To list all markdown notes, use `pattern: "*.md"` under the vault path.
- To list a subfolder, search under that subfolder's absolute path.

## Search

Use `search_files` for both filename and content searches. Prefer this over `grep`, `find`, or `ls`.

- For filenames, use `search_files` with `target: "files"` and a filename `pattern`.
- For note contents, use `search_files` with `target: "content"`, the content regex as `pattern`, and `file_glob: "*.md"` when you want to restrict matches to markdown notes.

## Create a note

Use `write_file` with the resolved absolute path and the full markdown content. Prefer this over shell heredocs or `echo` because it avoids shell quoting issues and returns structured results.

## Append to a note

Prefer a native file-tool workflow when it is not awkward:

- Read the target note with `read_file`.
- Use `patch` for an anchored append when there is stable context, such as adding a section after an existing heading or appending before a known trailing block.
- Use `write_file` when rewriting the whole note is clearer than constructing a fragile patch.

For an anchored append with `patch`, replace the anchor with the anchor plus the new content.

For a simple append with no stable context, `terminal` is acceptable if it is the clearest safe option.

## Targeted edits

Use `patch` for focused note changes when the current content gives you stable context. Prefer this over shell text rewriting.

## Memory System (Long-Term Memory)

This vault is the **long-term memory system** for Hermes. Treat it as persistent storage that survives across sessions.

### Memory File Structure
```
Obsidian-Vault/
├── Memory/
│   ├── About Me.md          — User profile, skills, projects
│   ├── Goals.md             — Short/medium/long-term goals
│   ├── Current Projects.md  — Active project statuses
│   ├── Preferences.md       — User preferences, communication style, tool prefs
│   ├── Lessons Learned.md   — Technical lessons, troubleshooting
│   ├── Decisions Log.md     — Key decisions with dates
│   ├── Daily Journal.md     — Daily activity log
│   └── Knowledge Base/      — Technical reference docs
└── (other user folders)
```

### Before answering questions:
1. Read relevant memory files for context (`About Me`, `Preferences`, `Current Projects`, `Lessons Learned`)
2. Search vault content for related notes using `search_files`

### After learning something important:
1. Update the appropriate memory file (e.g., new preference → `Preferences.md`)
2. Log new lessons to `Lessons Learned.md`
3. Update project status in `Current Project.md`
4. Append significant events to `Daily Journal.md`
5. Record key decisions in `Decisions Log.md`

### User instruction:
> "Treat my Obsidian vault as long-term memory. Before answering, search relevant notes. When important new information about my preferences, projects, decisions, or learnings appears, update the appropriate memory files with concise summaries."

## Memory System (Long-Term Memory)

This vault is the **long-term memory system** for Hermes. Treat it as persistent storage that survives across sessions.

### Memory File Structure
```
Obsidian-Vault/
└── Memory/
    ├── About Me.md          — User profile, skills, projects
    ├── Goals.md             — Short/medium/long-term goals
    ├── Current Projects.md  — Active project statuses
    ├── Preferences.md       — User preferences, communication style
    ├── Lessons Learned.md   — Technical lessons, troubleshooting
    ├── Decisions Log.md     — Key decisions with dates
    ├── Daily Journal.md     — Daily activity log
    └── Knowledge Base/      — Technical reference docs
        └── Hermes Agent.md
```

### When answering questions:
1. **Before answering** — Read relevant memory files for context (especially `About Me.md`, `Preferences.md`, `Current Projects.md`)
2. **After learning something new** — Propose updates to the appropriate memory file
3. **After completing tasks** — Update `Current Projects.md` and append to `Daily Journal.md`
4. **When making mistakes** — Add to `Lessons Learned.md`
5. **After important decisions** — Add to `Decisions Log.md`

### Memory instruction for user:
> "Treat my Obsidian vault as long-term memory. Before answering, search relevant notes. When important new information about my preferences, projects, decisions, or learnings appears, update the appropriate memory files with concise summaries."
