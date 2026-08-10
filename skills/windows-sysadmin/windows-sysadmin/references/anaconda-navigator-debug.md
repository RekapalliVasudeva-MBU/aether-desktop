# Anaconda Navigator Won't Start — Debug Recipe

## Symptoms
- Clicking Anaconda Navigator in Start Menu → nothing happens
- Running `anaconda-navigator` in terminal → exits immediately with "Please activate the conda root environment properly" or no output at all
- `where conda` returns nothing in git-bash

## Root Cause
Anaconda installed at `C:\ProgramData\anaconda3` but its paths are NOT in the system PATH. The `anaconda-navigator.exe` is a Qt GUI app that requires conda environment activation first.

## Quick Diagnosis
```bash
# Check if conda is in PATH
cmd /c "where.exe conda"

# Check installation exists
cmd /c "dir /b C:\ProgramData\anaconda3\Scripts\anaconda-navigator.exe"

# Check conda environments
type C:\Users\valte\.conda\environments.txt

# Try launching with activation
cmd /c "C:\ProgramData\anaconda3\Scripts\activate.bat root && C:\ProgramData\anaconda3\Scripts/anaconda-navigator.exe"
```

## Fixes

### Option 1: Use Anaconda Prompt (simplest)
Open Start Menu → search "Anaconda Prompt" → run `anaconda-navigator` from there.

### Option 2: Add to System PATH (permanent)
Add these to your system environment variables:
```
C:\ProgramData\anaconda3
C:\ProgramData\anaconda3\Scripts
C:\ProgramData\anaconda3\Library\bin
C:\ProgramData\anaconda3\condabin
```

### Option 3: One-shot launch
```
cmd /c "C:\ProgramData\anaconda3\Scripts\activate.bat root && C:\ProgramData\anaconda3\Scripts/anaconda-navigator.exe"
```

## Key Insight
GUI apps on Windows produce ZERO console output. MSYS/bash cannot properly launch or debug them. Always route through `cmd /c`. If the app still doesn't work after activation, check:
- Log files in `%USERPROFILE%\.anaconda\`
- Windows Event Viewer: `cmd /c "wevtutil qe Application /q:\"[System[Level=1 or Level=2]]\" /c:5 /f:text /rd:true"`
- Python import test: `cmd /c "python -c \"import anaconda_navigator; print('OK')\""`
