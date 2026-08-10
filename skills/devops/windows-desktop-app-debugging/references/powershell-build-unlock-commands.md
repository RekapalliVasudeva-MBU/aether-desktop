# PowerShell Commands for Stubborn PyInstaller Build Locks

## When `rmdir /s /q dist_build` fails with "Access denied" or "used by another process"

### Method 1: Using openfiles (requires Admin PowerShell)
```powershell
$dir = 'C:\Users\<user>\<project>\dist_build\<app>'
$open = cmd /c 'openfiles /query /fo csv /v 2>$null' | ConvertFrom-Csv 2>$null
if ($open) {
    $matches = $open | Where-Object { $_.'Open File Path' -like "*$dir*" }
    if ($matches) {
        $matches | Format-Table 'Process ID', 'Open File Path', 'Access Type'
        foreach ($m in $matches) {
            Write-Host "Killing PID $($m.'Process ID')"
            Stop-Process -Id $m.'Process ID' -Force
        }
        Start-Sleep 3
    }
}
```

### Method 2: Kill all WebView2/Aether child processes
```powershell
Get-Process -Name "*webview*","*msedgewebview2*","*Aether*" -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "Killed WebView2/Aether processes"
Start-Sleep 2
```

### Method 3: Force unlock with takeown/icacls
```powershell
cmd /c "takeown /f '$dir' /r /d y 2>$null"
cmd /c "icacls '$dir' /grant administrators:F /t /c /q 2>$null"
Start-Sleep 2
```

### Method 4: Final delete
```powershell
Remove-Item $dir -Recurse -Force -ErrorAction Stop
Write-Host "Deleted successfully"
```

## Complete One-Liner for Copy-Paste
```powershell
$dir = 'C:\Users\valte\aether\dist_build\Aether'
$open = cmd /c 'openfiles /query /fo csv /v 2>$null' | ConvertFrom-Csv 2>$null
if ($open) { $matches = $open | Where-Object { $_.'Open File Path' -like "*$dir*" }; if ($matches) { foreach ($m in $matches) { Stop-Process -Id $m.'Process ID' -Force }; Start-Sleep 3 } }
Get-Process -Name "*webview*","*msedgewebview2*","*Aether*" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 2
cmd /c "takeown /f '$dir' /r /d y 2>$null"
cmd /c "icacls '$dir' /grant administrators:F /t /c /q 2>$null"
Start-Sleep 2
Remove-Item $dir -Recurse -Force -ErrorAction Stop
Write-Host "Deleted successfully"
```

## Notes
- Requires **PowerShell as Administrator** for `openfiles`, `takeown`, `icacls`
- `openfiles /local on` must be enabled once (reboot required) for local file tracking
- WebView2 spawns GPU/utility child processes that persist after main exe dies
- Always run these BEFORE `python build_aether.py`