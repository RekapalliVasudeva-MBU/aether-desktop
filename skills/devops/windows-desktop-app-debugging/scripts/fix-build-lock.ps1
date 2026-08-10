#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Fix stubborn PyInstaller build directory locks caused by WebView2 child processes.
.DESCRIPTION
    Kills Aether/WebView2 processes, finds and releases file locks on the build directory,
    then removes the build directory so a clean rebuild can proceed.
.NOTES
    Requires PowerShell as Administrator for openfiles/takeown/icacls.
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$BuildDir = 'C:\Users\valte\aether\dist_build\Aether',

    [Parameter(Mandatory=$false)]
    [string]$WorkDir = 'C:\Users\valte\aether\build_aether'
)

Write-Host "=== PyInstaller Build Lock Fixer ===" -ForegroundColor Cyan
Write-Host "Target: $BuildDir" -ForegroundColor Yellow

# Step 1: Kill all Aether/WebView2 processes
Write-Host "`n[1/5] Killing Aether/WebView2 processes..." -ForegroundColor Green
Get-Process -Name "*Aether*","*webview*","*msedgewebview2*" -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "  Killed Aether/WebView2 processes" -ForegroundColor Gray
Start-Sleep 2

# Step 2: Find and kill processes locking the build directory via openfiles
Write-Host "[2/5] Checking openfiles for locks on $BuildDir..." -ForegroundColor Green
try {
    $open = cmd /c "openfiles /query /fo csv /v 2>$null" | ConvertFrom-Csv 2>$null
    if ($open) {
        $matches = $open | Where-Object { $_.'Open File Path' -like "*$BuildDir*" }
        if ($matches) {
            $matches | Format-Table 'Process ID', 'Open File Path', 'Access Type'
            foreach ($m in $matches) {
                $pid = $m.'Process ID'
                Write-Host "  Killing PID $pid ($($m.'Access Type'))" -ForegroundColor Yellow
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            }
            Write-Host "  Killed $($matches.Count) locking process(es)" -ForegroundColor Green
            Start-Sleep 3
        } else {
            Write-Host "  No openfiles locks found" -ForegroundColor Gray
        }
    } else {
        Write-Host "  openfiles returned no data (run 'openfiles /local on' + reboot if needed)" -ForegroundColor Gray
    }
} catch {
    Write-Warning "openfiles check failed: $_"
}

# Step 3: Also check Get-Process modules for locks
Write-Host "[3/5] Checking Get-Process modules for locks..." -ForegroundColor Green
$locked = Get-Process | Where-Object {
    try { $_.Modules.FileName -like "*$BuildDir*" } catch { $false }
}
if ($locked) {
    $locked | Select-Object -Unique Id, ProcessName, Path | Format-Table
    $locked | Select-Object -Unique Id | ForEach-Object { Stop-Process -Id $_.Id -Force }
    Write-Host "  Killed $($locked | Select-Object -Unique Id).Count locking process(es)" -ForegroundColor Green
    Start-Sleep 2
} else {
    Write-Host "  No module locks found" -ForegroundColor Gray
}

# Step 4: Force unlock with takeown/icacls
Write-Host "[4/5] Running takeown/icacls on $BuildDir..." -ForegroundColor Green
if (Test-Path $BuildDir) {
    cmd /c "takeown /f `"$BuildDir`" /r /d y 2>$null"
    cmd /c "icacls `"$BuildDir`" /grant administrators:F /t /c /q 2>$null"
    Write-Host "  takeown/icacls completed" -ForegroundColor Green
    Start-Sleep 2
}

# Step 5: Final delete
Write-Host "[5/5] Removing $BuildDir and $WorkDir..." -ForegroundColor Green
$deleted = $false
for ($i = 1; $i -le 5; $i++) {
    try {
        if (Test-Path $BuildDir) { Remove-Item $BuildDir -Recurse -Force -ErrorAction Stop }
        if (Test-Path $WorkDir) { Remove-Item $WorkDir -Recurse -Force -ErrorAction Stop }
        Write-Host "  SUCCESS: Build directories deleted" -ForegroundColor Green
        $deleted = $true
        break
    } catch {
        Write-Host "  Attempt $i failed: $($_.Exception.Message)" -ForegroundColor Red
        Start-Sleep 2
    }
}

if (-not $deleted) {
    Write-Host "`nFAILED: Could not delete build directories after 5 attempts." -ForegroundColor Red
    Write-Host "Try restarting Windows, then run this script again." -ForegroundColor Yellow
    exit 1
}

Write-Host "`n=== SUCCESS: Build directories cleaned, ready for rebuild ===" -ForegroundColor Cyan
Write-Host "Run: python build_aether.py" -ForegroundColor Cyan