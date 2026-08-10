# Disk Cleanup Quick Reference

## Standard Cleanup Checklist

When the user asks to free disk space, check these locations in order:

### 1. npm-cache (often 2-5 GB)
Check and delete:
```
rm -rf ~/AppData/Local/npm-cache
```

### 2. pip cache (often 100-500 MB)
```
rm -rf ~/AppData/Local/pip/cache
```

### 3. Temp folder (often 500MB-2GB)
Look for large installers: `WinGet/`, `*-installer-*` folders.

### 4. Recycle Bin
```powershell
Clear-RecycleBin -Force
```

### 5. AppData leftovers from uninstalled programs
Check Local, Roaming, LocalLow for deleted program folders.

## Program Files Deletion Rule

**Files in `C:\Program Files\` or `C:\Program Files (x86)\` ALWAYS need admin privileges.**

When "Access is denied" (WinError 5) in Program Files:
1. Do NOT retry — it will always fail without admin
2. Tell the user to run as Administrator:
   ```
   rmdir /s /q "C:\Program Files\<folder>"
   ```
3. Or have them right-click → Delete (Windows prompts for admin)

## Space Reporting

Always report how much space was freed after cleanup using `shutil.disk_usage`.
