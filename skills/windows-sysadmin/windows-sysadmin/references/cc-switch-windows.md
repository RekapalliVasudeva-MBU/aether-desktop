# CC Switch — Windows Installation Notes

## Status: Uninstalled (2026-06-10)
User found the app not useful. All traces removed including shortcuts, installers, and temp files.

## What It Is
CC Switch (v3.16.2) — All-in-One Manager for Claude Code, Codex, Gemini CLI, OpenCode, OpenClaw, and Hermes Agent.
- Manages API providers, MCP servers, Skills, and Prompts across 7 AI tools
- Built with Tauri 2 (Rust backend + React frontend)
- Official site: https://ccswitch.io

## Installation (Windows) — For Future Reference
- **Preferred method:** Download `CC-Switch-v3.16.2-Windows-Portable.zip` from GitHub Releases
- Extract to `C:\\Users\\<user>\\CC-Switch\\`
- Run `cc-switch.exe` directly — no installer needed
- Create shortcut on the **correct** Desktop (check registry for OneDrive path)
- **Do NOT build from source** — Rust toolchain requires GUI installer that fails from MSYS

## "Commits Behind" Display
The app shows "X commits behind" comparing against the `main` development branch, **not** the latest release tag. This means:
- v3.16.2 may show "52 commits behind" even though it's the latest stable release
- The `main` branch has unreleased development commits
- This is a display quirk, not an actual update being available
- The built-in updater checks GitHub Releases (tags), not the branch

## Update Check
Latest release as of 2026-06-10: **v3.16.2** (published 2026-06-08)
- Only 1 commit ahead of the release tag (minor proxy fix)
- No newer stable release available

## Data Locations
- Database: `~/.cc-switch/cc-switch.db` (SQLite)
- Settings: `~/.cc-switch/settings.json`
- Backups: `~/.cc-switch/backups/`
- Skills: `~/.cc-switch/skills/`
