---
name: nextjs-dashboards
description: "Build local-first Next.js dashboards with Tailwind CSS and glassmorphism UI — agent OS control panels, monitoring UIs, and shortcut launchers."
platforms: [windows, linux, macos]
---

# Next.js Dashboards

Build locally-hosted dashboard UIs with Next.js (App Router), Tailwind CSS v4, and modern glassmorphism patterns. Tailored for agent OS control panels, AI tool dashboards, and shortcut launchers.

## When To Use

- User wants a local UI dashboard for managing AI agents, tools, or system controls
- Glassmorphism / terminal-aesthetic / "mission control" style is requested
- Next.js + Tailwind is the chosen stack (or acceptable)

## Stack & Versions

**Pin Next.js version on Node v24+** — `create-next-app@latest` can hang. Use pinned version:
```bash
npx create-next-app@15 <app-name> --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --yes
```

**Tailwind v4** is the default in Next.js 15. Config is CSS-only (no `tailwind.config.js`):
```css
/* globals.css */
@import "tailwindcss";
```

**Lucide React** for icons:
```bash
npm install lucide-react
```

## Project Structure

```
src/app/
├── globals.css       # Tailwind import + custom CSS variables
├── layout.tsx        # Minimal — just import globals.css
└── page.tsx          # Main dashboard component
```

## Working Patterns

### Glassmorphism Card Component
```css
.glass-card {
  background: linear-gradient(135deg, rgba(17, 24, 39, 0.8), rgba(17, 24, 39, 0.6));
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 12px;
  transition: all 0.3s ease;
}
.glass-card:hover {
  border-color: rgba(255, 255, 255, 0.15);
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.1);
}
```

### Dark Mission Control Background
```css
body {
  background-color: #0B0F19;
  background-image:
    linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
  background-size: 32px 32px;
}
```

### Status Glow Indicators
```css
.status-online   { box-shadow: 0 0 12px rgba(34, 197, 94, 0.4); }  /* green */
.status-running  { box-shadow: 0 0 12px rgba(59, 130, 246, 0.4); } /* blue */
.status-paused   { box-shadow: 0 0 12px rgba(245, 158, 11, 0.4); } /* amber */
```

### Heartbeat Animation (Live System Indicator)
```css
@keyframes heartbeat {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
.heartbeat { animation: heartbeat 1.5s ease-in-out infinite; }
```

### Terminal-Styled Text
```css
.terminal-text {
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
}
```

### Sidebar Quick Links Pattern
For adding external tool shortcuts (ChatGPT, Gemini, Obsidian) to the sidebar:
```tsx
const quickLinks = [
  { label: 'ChatGPT', url: 'https://chatgpt.com', icon: <MessageSquare size={13} />, color: 'text-green-400' },
  { label: 'Gemini', url: 'https://gemini.google.com', icon: <Sparkles size={13} />, color: 'text-blue-400' },
  { label: 'Obsidian', url: 'obsidian://open?vault=Obsidian-Vault', icon: <BookOpen size={13} />, color: 'text-purple-400' },
];
```

### Simulated Streaming Data Hook
```tsx
function useStreamLines(source: string[], delay = 2500) {
  const [lines, setLines] = useState<string[]>([]);
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    const i = setInterval(() => {
      setLines(prev => [...prev.slice(-15), source[idx % source.length]]);
      setIdx(i => i + 1);
    }, delay);
    return () => clearInterval(i);
  }, [idx, delay, source]);
  return lines;
}
```

## Verification

1. Build: `npm run build` — fix any errors before proceeding
2. Production start: `npx next start -p <port>` (NOT `next dev` for long-running serving)
3. Verify: `curl -s -o /dev/null -w "%{http_code}" http://localhost:<port>` → expect `200`

## Windows-Specific Notes

- Dev server must run via `terminal(background=true)`, NOT with `&` in foreground
- **Desktop shortcut path**: The real desktop is `C:\Users\<user>\OneDrive\Desktop` when OneDrive sync is active, NOT `C:\Users\<user>\Desktop`. Always verify with `[Environment]::GetFolderPath('Desktop')` in PowerShell.
- **PowerShell in bash**: `$_.CommandLine`, `$($_.Id)` etc. break when passed through bash/MSYS. Write `.ps1` script files and run with `powershell -File "script.ps1"` instead.
- **winget --silent can fail**: If silent install fails with exit code 3221225477, find the downloaded .exe in `AppData\Local\Temp\WinGet\<package>\` and run it directly.
- **Create .url shortcuts** for HTTP links on desktop. Use `[InternetShortcut]` format. Create on the OneDrive Desktop path.

## API Route Pattern (Dashboard → Local Tools)

```
src/app/api/<resource>/route.ts   — GET for reads, POST for actions
```

**Important:** Avoid dynamic `[id]` params on the SAME path as a parent route with POST — Next.js type system rejects it. Handle all actions in one route via `{ action }` in the POST body.

**child_process in API routes:** `execSync` with hardcoded commands (no user input) is safe. Document: `// Safe: hardcoded command, no user input`

**Obsidian vault integration:**
- Read vault files via `execSync('powershell -Command "Get-Content -Path ... -Raw -Encoding UTF8"')`
- Exclude `.obsidian/` folder from file listings
- Deep link to vault: `obsidian://open?vault=<VaultName>` (folder name, not path)
- Memory folder structure gives Hermes persistent long-term memory

## Pitfalls

- **Desktop shortcut path on OneDrive machines**: Always check `[Environment]::GetFolderPath('Desktop')` — it may return `OneDrive\Desktop`, not `Desktop`. This is the #1 reason shortcuts "don't show up".
- **PowerShell variable interpolation in bash**: Write `.ps1` files instead of inline PowerShell with `$_.` variables.
- **Port 3000 conflict on this machine**: Port 3000 = WhatsApp bridge (Baileys). Use port 3001+ for dashboards.
- **Duplicate `lucide-react` icon imports**: Same icon in two import lines causes `Module parse failed`. Deduplicate.
- **`React.useRef` in module scope**: Import `useRef` directly, not `React.useRef`.
- **Heredocs with special chars**: `***`, backticks get mangled in git-bash. Write scripts to files first.
- **`.url` vs `.lnk` shortcuts**: `.url` for HTTP links on desktop. `.lnk` (via WScript.Shell COM) for Start Menu.
- Don't use `window:` background operator in foreground `terminal()` calls
- Don't skip `npm run build` verification before declaring success
- **SWC chokes on inline generics in `.tsx`**: `useState<TypeName>(initial)` inside a `.tsx` file can cause `Syntax Error: Expected '</', got ':'` — the SWC parser treats `<TypeName>` as a JSX tag. **Fix**: extract all interfaces/types to a separate `types.ts` file and `import type` from it. This also applies to inline object type annotations on function parameters — use a pre-declared `type` alias instead.
- **Box-drawing/Unicode chars in comments break the build**: Characters like `─` (U+2500 Box Drawings Light Horizontal), `·` (U+00B7 Middle Dot), and `—` (U+2014 Em Dash) inside JSX text or comments can cause parse errors or invisible character corruption. **Fix**: always use plain ASCII hyphens `-` for separators, regular dots `.`, and double hyphens `--` for emphasis. Use a tool like `cat -A` or a Unicode scanner to detect these before debugging mysterious build failures.
- **`patch` tool partial-read warning**: If `page.tsx` (or any large file) was read with `offset/limit`, the `patch` tool logs a warning. Always re-read the full file (no offset/limit) before patching large files — otherwise edits may add duplicate content or miss context.
- `next dev` is for development only — use `next start -p <port>` for long-running serving
- `patch` tool can't edit `config.yaml` — use `terminal()` + `sed`
- `read_file` blocks `.env` files — use `grep` via `terminal()` to check keys
