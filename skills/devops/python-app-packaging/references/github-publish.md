# Publishing a frozen Python app to GitHub — safely

Context: shipping an AetherMind-style app where the website (web RAG server) and
the desktop app are TWO related but separate deliverables. The user wants a
2-in-1 story told clearly, private repos, and ZERO leaked credentials.

## Repo split (2-in-1)
Split into two repos so each is independently clonable and the website can host
the desktop download:
- `<org>/project_rag` — the web RAG server + website (serves `/download/aether`,
  `/aether-docs`, the public landing page).
- `<org>/aether-desktop` — the desktop app source (FastAPI + pywebview + build
  scripts + `make_installer.py`).

Each README links to the other and states the 2-in-1 relationship in a table:
| Repo | What it is |
so GitHub visitors immediately get "this is one product, two delivery modes."

## Hard rules (this user)
- **Repos MUST be private.** Create with `gh repo create <org>/<name> --private`.
  The user flips public manually after review — never the agent.
- **No credentials in the repo.** The distributed exe ships WITHOUT any API key;
  the key is pasted in-app and stored only in `%APPDATA%/aether/.env` (gitignored).
- `gh` must be authenticated first (`gh auth login` / a fine-grained PAT with
  `repo` scope). The agent cannot create or push repos unauthenticated.

## Cross-shell `gh auth` gap (Windows MSYS/bash agent shell)
The user often runs `gh auth login` in their **PowerShell/CMD** window, but the
agent's terminal runs in a **separate MSYS bash** environment. The two do NOT
share `gh`'s auth token cache, so even after a successful browser login in
PowerShell, `gh auth status` inside the agent shell reports
`You are not logged into any GitHub hosts.` The token IS valid (stored under the
Windows user profile) — `gh` just can't find it in the bash shell's context.

**Symptom:** `gh auth login` succeeded in PowerShell, but in the agent shell:
```
gh auth status  →  You are not logged into any GitHub hosts.
gh api user      →  please run gh auth login
```
yet a raw API call with the token works:
```
curl -H "Authorization: Bearer <tok>" https://api.github.com/user   →  {"login":"..."}
```

**Fix (no re-login needed):** extract the stored oauth token and export it as
`GH_TOKEN` in the agent shell. `gh` reads `GH_TOKEN` and authenticates immediately:
```bash
export GH_TOKEN=$(gh config get -h github.com oauth_token 2>/dev/null)
gh auth status        # now: ✓ Logged in to github.com account <user> (GH_TOKEN)
gh api user --jq .login
```
`export` persists for the rest of the session (shell state carries across calls),
so subsequent `gh repo create` / `gh push` work without repeating this. If
`gh config get` returns empty, fall back to a fine-grained PAT pasted as
`GH_TOKEN`, or have the user re-run `gh auth login` *inside* the agent's shell.
Note: `GH_TOKEN` in the env is fine for the session; do NOT write it to any file
that could be committed.

## .gitignore traps (hit this session)
- **`nul` device file breaks `git add`.** A stray Windows `nul` (named pipe /
  device) file in the working tree makes `git add -A` fail with
  `error: short read while indexing nul` / `fatal: adding files failed`.
  FIX: `rm -f nul` (and add `nul` + `nul/` to `.gitignore`), then `git add -A`.
- **ChromaDB binary dirs must be ignored.** `rag_vector_db/` (UUID subfolders with
  `*.bin`/`header.bin`/`length.bin`) and `chroma/` bloat the repo and aren't
  source. Add `rag_vector_db/`, `chroma/`, `rag_pdfs/`, `sessions/`,
  `session_backups/`, `*.log`, `dist/`, `*.exe`, `*.zip`, `server_config.json`,
  `config.yaml` to `.gitignore`.
- Include a `.env.example` (documents required env vars, NO values) so users know
  what to set without you committing the real `.env`.

## Pre-push secret scan (run BEFORE every push)
After `git add -A`, scan the STAGED tree (not the working tree) for real values:
```bash
git diff --cached --name-only | xargs grep -lI -E \
  "sk-or-[A-Za-z0-9]{20,}|OPENROUTER_API_KEY\s*=\s*[\"']sk|NGROK_AUTH[A-Z]*\s*=\s*[\"'][A-Za-z0-9]{20,}" \
  2>/dev/null || echo "NO SECRETS"
```
Note: env-VAR *names* in code (e.g. `os.environ.get("OPENROUTER_API_KEY")`) are
fine — only `KEY=value` assignments with an actual secret-shaped RHS are banned.
If a match is a real value, `git rm --cached <file>` + fix, do NOT commit it.

## GitHub push failures — HTTP 408 timeout & non-fast-forward (hit this session)

Two distinct push failures happened while shipping the desktop app. Both are
recoverable and BOTH stem from `git add -A` sweeping build artifacts.

### (a) HTTP 408 `the remote end hung up unexpectedly` (pack upload timeout)
Symptom: `git push` runs, shows `Recv header: X-Frame-Options: DENY`, then dies
with `error: RPC failed; HTTP 408 curl 22 ... fatal: the remote end hung up
unexpectedly`. No "large file" / "deny" message — it's a SLOW upload that the
server timed out. Root cause: the committed tree contains LARGE blobs
(build dirs, old `.exe` onefile builds, chroma `.sqlite3`, `*.iss`-test exes)
so the pack is huge and the connection is throttled. Confirm with:
`git rev-list --objects HEAD | git cat-file --batch-check='%(objecttype) %(objectsize) %(rest)' | awk '$1=="blob"{print $2,$3}' | sort -rn | head`
If you see blobs >10 MB (e.g. `aether_test2.exe` 94 MB, `build_aether/Aether/Aether.exe`
36 MB, `deploy/rag_vector_db/chroma.sqlite3` 8 MB), those are the killers.
FIX: add them to `.gitignore` (`build_aether/`, `dist_build/`, `dist/`, `*.exe`,
`deploy/`, `*.spec`), then `git rm -r --cached --quiet <those dirs>`, `git add -A`,
`git commit --amend` (or new commit), re-push. After this the largest blob is
~16 KB and the push takes seconds.

### (b) `failed to push some refs` with NO detail (non-fast-forward divergence)
Symptom: `git push` exits `error: failed to push some refs to '...'` but `git
ls-remote --heads origin` shows the remote `main` is at a DIFFERENT commit than
your local base, and `git log --oneline --left-right HEAD...origin/main` shows
only YOUR commit on the left (remote's commits not reachable from HEAD). Your
local branch diverged from the remote (a prior session pushed commits you don't
have locally, or you reset/rebased). FIX: `git fetch origin`, then
`git rebase origin/main` (puts your commit on top of the remote history — fast
forward now possible), then `git push -u origin main`. Do NOT force-push unless
the remote history is genuinely unwanted; rebase preserves it.

### Rule that prevents both: NEVER `git add -A` a build tree
PyInstaller outputs (`dist/`, `dist_build/`, `build_aether/`) + Inno outputs
(`*.exe`, `*.iss`) + runtime DBs (`deploy/`, `rag_vector_db/`) MUST be in
`.gitignore` BEFORE the first commit. `git add -A` in a repo that also has these
folders will commit 3000+ files and cause the 408. Verify cheaply after commit:
`git ls-files | wc -l` (should be ~100 for a source-only repo, NOT 3000+).

## Sequence that worked
1. `git init` in each repo root; drop in `.gitignore` + `.env.example` + `README.md`.
2. `git add -A`; if `nul` error → `rm -f nul`, re-add. Check `git ls-files | wc -l`
   is small (source only).
3. Run the staged secret scan above; confirm CLEAN.
4. `git commit -m "..."` locally (captures work even before auth).
5. Once `gh` is authed: `gh repo create <org>/<name> --private`, `git branch -M main`,
   `git remote add origin ...`, `git fetch origin` (in case remote has prior
   history), `git rebase origin/main` if diverged, then `git push -u origin main`.
6. Verify on github.com that the repo is private and contains no `.env`/key files
   and no large build blobs.
