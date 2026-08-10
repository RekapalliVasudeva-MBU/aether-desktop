# Eclipse Workspace Cleanup

## When to Use
User wants to delete all Eclipse junk — workspaces, project folders, cached metadata, and installer remnants — to start fresh.

## What to Delete

| Path | What it is | Safe to delete? |
|------|-----------|-----------------|
| `C:\Users\<user>\eclipse-workspace\` | Workspace (projects, .metadata) | Yes — projects must be re-imported |
| `C:\Users\<user>\.eclipse\` | Oomph setup cache, product configs | Yes — regenerated on next launch |
| `C:\Users\<user>\Downloads\eclipse-*.zip` | Eclipse installer ZIP | Yes |
| `C:\Users\<user>\Downloads\eclipse-*\` | Extracted Eclipse folder | Yes |
| `C:\Program Files\Eclipse\` | System-wide Eclipse install | Needs admin |

## Important: Don't Delete
- `C:\Users\<user>\AppData\Local\` except the Eclipse-specific dirs above
- `C:\Users\<user>\Documents\` — user files, not Eclipse junk

## Verification After Cleanup
```powershell
# Check workspace is empty
Test-Path "C:\Users\<user>\eclipse-workspace"
# Check .eclipse config is gone
Test-Path "C:\Users\<user>\.eclipse"
```

## Reinstall Steps
1. Download Eclipse IDE for Java Developers from https://www.eclipse.org/downloads/
2. Extract ZIP to `C:\eclipse\` (permanent location)
3. Create Desktop shortcut: right-click `C:\eclipse\eclipse.exe` → Send to → Desktop
4. Launch → set workspace to `C:\Users\<user>\eclipse-workspace`
5. Create project → right-click → New → Java Project → use JavaSE-21 (not JavaSE-26)
