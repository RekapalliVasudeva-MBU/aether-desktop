---
name: github-workflow
description: "Complete GitHub workflow: authentication, repository management, PR lifecycle, code review, and issue management. Use when working with GitHub — cloning, creating, forking repos; branching, committing, pushing, opening PRs; reviewing code, leaving comments; creating, triaging, labeling issues. Covers both gh CLI and git+curl REST fallbacks."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [github, git, pull-requests, issues, code-review, repositories, auth, gh-cli]
---

# GitHub Workflow

Complete GitHub workflow via `gh` CLI (preferred) or `git` + `curl` REST fallback.

## Auth Detection (Run First)

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="curl"
  # Extract token from git-credentials or ~/.hermes/.env
fi
```

## Owner/Repo Extraction

```bash
REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
```

---

## §1 — Authentication

### Git-Only (No gh, No sudo)

**HTTPS with Personal Access Token:**
1. Create token at https://github.com/settings/tokens (scopes: `repo`, `workflow`)
2. `git config --global credential.helper store`
3. Push to trigger auth — paste token as password

**SSH Key:**
```bash
ssh-keygen -t ed25519 -C "email" -f ~/.ssh/id_ed25519 -N ""
# Add public key at https://github.com/settings/keys
ssh -T git@github.com
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

### gh CLI Auth

```bash
gh auth login                    # interactive
echo "<TOKEN>" | gh auth login --with-token  # headless
gh auth setup-git               # configure git credentials
```

### API Token from Git Credentials

```bash
grep "github.com" ~/.git-credentials | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|'
```

---

## §2 — Repository Management

### Clone

```bash
git clone https://github.com/owner/repo.git
gh repo clone owner/repo
```

### Create

```bash
# With gh
gh repo create my-project --public --clone

# With curl
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user/repos \
  -d '{"name": "my-project", "private": false}'
```

### Fork

```bash
gh repo fork owner/repo --clone

# With curl
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/owner/repo/forks
git clone https://github.com/$GH_USER/repo.git
git remote add upstream https://github.com/owner/repo.git
```

### Keep Fork Synced

```bash
git fetch upstream && git checkout main && git merge upstream/main && git push origin main
```

### Settings & Releases

```bash
gh repo edit --description "..." --visibility public
gh release create v1.0.0 --generate-notes
gh release create v1.0.0 ./dist/binary --title "v1.0.0"
```

**Large binary distribution (>300 MB):** GitHub Releases serves assets from a fast
global CDN (`objects.githubusercontent.com`) at line speed — far better than tunneling
big files through ngrok (which rate-limits to <2 Mbps). For a packaged desktop app
installer: `gh release create v1.0.0 dist/App-Setup.exe --repo <owner>/<repo> --title
"v1.0.0" --notes "..."` (2 GB file limit). The asset URL is
`https://github.com/<owner>/<repo>/releases/download/v1.0.0/App-Setup.exe` — point
website buttons + READMEs there. To keep legacy links working, make the site's
download route a 302 `RedirectResponse` to that URL instead of serving the file.

**Cross-shell `gh auth` gap (Windows/MSYS):** `gh auth login` run in a PowerShell window
is often INVISIBLE to the agent's MSYS bash shell — `gh auth status` still reports "not
logged in" even though the browser flow succeeded. The token IS stored, though. Recover:
`export GH_TOKEN=$(gh config get -h github.com oauth_token)` then re-run `gh auth
status` → it shows `Logged in ... (GH_TOKEN)`. This unblocks `gh repo create` / `gh
release` / `gh push` without re-authenticating.

---

## §3 — PR Lifecycle

### Branch → Commit → Push → PR

```bash
git checkout main && git pull origin main
git checkout -b feat/add-feature
# (make changes)
git add . && git commit -m "feat: add feature"
git push -u origin HEAD
gh pr create --title "feat: add feature" --body "Closes #42"
```

### Monitor CI

```bash
gh pr checks
gh pr checks --watch
```

### Merge

```bash
gh pr merge --squash --delete-branch
gh pr merge --auto --squash --delete-branch
```

### Auto-Fix CI Failures

1. `gh run list --branch $(git branch --show-current) --limit 5`
2. `gh run view <RUN_ID> --log-failed`
3. Fix, commit, push, re-check

---

## §4 — Code Review

### Review Local Changes (Pre-Push)

```bash
git diff main...HEAD --stat    # scope
git diff main...HEAD           # full diff
```

### Review a PR

```bash
gh pr view 123
gh pr diff 123
git fetch origin pull/123/head:pr-123 && git checkout pr-123
```

### Leave Comments

```bash
gh pr comment 123 --body "LGTM!"
gh pr review 123 --approve --body "L!"
gh pr review 123 --request-changes --body "See inline comments."
```

### Inline Review (curl)

```bash
# Get HEAD SHA, then POST review with inline comments
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/123/reviews \
  -d '{"event": "REQUEST_CHANGES", "body": "Issues found", "comments": [{"path": "f.py", "line": 42, "body": "SQL injection risk"}]}'
```

### Review Checklist

- **Correctness:** Edge cases, error paths
- **Security:** No secrets, input validation, parameterized queries
- **Quality:** Clear naming, DRY, focused functions
- **Testing:** Happy + error paths covered

---

## §5 — Issue Management

### Create

```bash
gh issue create --title "Bug: login redirect broken" --body "..." --label "bug" --assignee "@me"
```

### Triage

```bash
gh issue list --label "needs-triage" --state open
gh issue view 42
gh issue edit 42 --add-label "priority:high,bug" --add-assignee username
gh issue close 42
```

### Link Issues to PRs

Include `Closes #42`, `Fixes #42`, or `Resolves #42` in PR body.

---

## Quick Reference Table

| Action | gh | curl endpoint |
|--------|-----|--------------|
| Clone | `gh repo clone o/r` | `git clone https://github.com/o/r.git` |
| Create repo | `gh repo create name --public` | `POST /user/repos` |
| Fork | `gh repo fork o/r` | `POST /repos/o/r/forks` |
| Create PR | `gh pr create ...` | `POST /repos/o/r/pulls` |
| Merge PR | `gh pr merge --squash` | `PUT /repos/o/r/pulls/N/merge` |
| List issues | `gh issue list` | `GET /repos/o/r/issues` |
| Create issue | `gh issue create ...` | `POST /repos/o/r/issues` |
| Set secret | `gh secret set KEY` | `PUT /repos/o/r/actions/secrets/KEY` |
