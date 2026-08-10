---
name: verified-code-delivery
description: Discipline for delivering coding work to this user — actually read, edit, run, and verify with REAL tool output before claiming success. Never fabricate green-check summaries. Triggers on "fix it and run it", "u run it", "see the errors ok run all of then", "why cant u read it its py file right just access it and fix", or any pasted terminal traceback.
---

# Verified Code Delivery

## When to use
Any time you are asked to build, fix, convert, run, or explain code for this user — especially when they paste a raw terminal error and say "fix it and run it", "u run it", "see the errors ok run all of then", "run the project once", or "why cant u read it its py file right just access it and fix".

## Core rule
**Do the work, then PROVE it with real execution. Never narrate a success you did not actually produce.**

This user has been burned repeatedly by agents emitting confident `✅ SUCCESS / SYSTEM WORKING / 🎉 PIPELINE GENERATED` blocks that described fixes which were never run or even applied. That is the #1 failure mode to avoid. A fabricated green-check summary is worse than a correct "it failed, here's the traceback" — it wastes the user's time and destroys trust.

## Steps (in order, every time)
1. **Read the actual file** with `read_file` before editing. Do not reason about a file you haven't opened. If a path errors, fix the path — do NOT invent the file's contents.
2. **Edit with `patch` / `write_file`** — apply the real change; confirm the diff.
3. **Run it for real** — execute the actual entry point via `terminal` / `python` (e.g. `main.py`, NOT a deleted `src/...` helper). Capture real stdout/stderr.
4. **Report the real result** — paste the relevant output lines. If it failed, show the actual traceback and keep fixing. If it succeeded, show the proof (e.g. "DB CONTAINS 380 CHUNKS", or the model's actual generated answer).

## Anti-patterns (this user will reject these on sight)
- Emitting `✅ successfully converted / ✅ working / 🎉 SUCCESS` without having executed anything.
- Claiming a file was "fixed" when you never read or patched it.
- Answering a "why is there an error" question with a generic success recap instead of reproducing the error.
- Telling the user the code "is working perfectly" while they are literally pasting a fresh traceback.
- Pointing the run command at a file that doesn't exist (e.g. a deleted module) — verify the target file exists first.
- Repeating the SAME fabricated success paragraph across multiple turns after the user says it's wrong.

## Pitfalls discovered (encode these)
- **Reading loop:** When stuck on a bug, do NOT keep reading the same files over and over. If you've read a file 3+ times without applying a fix, you're in a loop. Stop reading, apply the fix based on what you already know, rebuild, and verify. The user's frustration ("stop reading", "just fix it", "don't fix anything now") is a signal — act on it immediately.
- **Wrong run target:** A multi-file `src/` package may be redundant scaffolding left from an earlier attempt; the real working entry point is often a single `main.py`. Confirm which file is actually executed before debugging imports. Deleting the dead `src/` tree is usually safe if nothing imports it.
- **"Only first item processed" bug:** loops like `for x in items[:1]` silently process one item. When the user expects ALL files/PDFs, remove the slice.
- **Stale/duplicate IDs in vector stores:** re-running with reset ids (`chunk_0`, `chunk_1`) collides with prior runs — make ids unique across items and/or `delete_collection` + recreate.
- **Module renamed across versions:** e.g. docling moved `InputFormat`/`PdfFormatOption` out of `docling.format_options` (see `references/docling_api.md`). When an import fails, check the installed package version and import from the CURRENT location rather than guessing.
- **Empty source files look like they have code:** Eclipse creates empty `.java` files with only a package declaration or Javadoc stub. These compile but produce no runnable output. Always check file contents with `cat` before debugging "why doesn't it run".
- **Eclipse Java version mismatch (JavaSE-26 vs JavaSE-21):** Eclipse `.classpath` may reference a JRE version that doesn't exist on the system, AND `.settings/org.eclipse.jdt.core.prefs` compiler settings (`source`, `targetPlatform`, `compliance`) must match the available JRE. If the compiler targets Java 26 but only Java 21 is available, the builder silently produces no `.class` files → `bin/` stays empty → nothing runs. Fix: align both `.classpath` JRE entry and `.settings/org.eclipse.jdt.core.prefs` compiler settings to the installed JRE version. Verify by checking `bin/` for `.class` files after a build.
- **Empty source files look like they have code:** Eclipse creates empty `.java` files with only a package declaration or Javadoc stub. These compile but produce no runnable output. Always check file contents with `cat` before debugging "why doesn't it run".
- **Smart caching must still write:** if "cache chunks to disk" is the goal, ensure even short inputs get a permanent file written (not just returned in-memory), or re-runs will re-split every time.

## Verification checklist BEFORE you say "done"
- [ ] Did I read the file I'm changing (not assume its contents)?
- [ ] Did I actually run the project (not just an import-check)?
- [ ] Is the output I'm quoting real terminal output from THIS session?
- [ ] Did the user's specific question get answered by real execution?

## References
- `references/docling_api.md` — docling 2.x import relocation (format_options removed) and how to probe the installed API.
