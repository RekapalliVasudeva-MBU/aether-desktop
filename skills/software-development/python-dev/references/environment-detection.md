# Python Environment Detection Guide

## Essential Environment Check Commands

**Copy these commands immediately to check your current environment:**

### 1. Primary Environment Detection
```powershell
# Windows Command Prompt or PowerShell - Run this NOW:
where python
python --version

# More detailed detection:
python -c "import sys; print('ENVIRONMENT:', sys.prefix); print('EXECUTABLE:', sys.executable); print('HOME:', sys.path[0][:100] if sys.path else 'NOT SET')"

# Check for conda vs hermes environment:
python -c "import sys; env = sys.prefix.lower(); is_hermes = 'hermes' in env; is_conda = 'conda' in env or 'anaconda' in env; print('Is Hermes sandbox:', is_hermes); print('Is Conda/Anaconda:', is_conda); print('Detected env:', env)"
```

### 2. Package Environment Check
```bash
# Different environments have different packages:
python -m pip list | grep -E "tensorflow|torch|lightning|pandas|numpy"

# In Hermes sandbox (for Hermes project development):
# - Limited packages: rich, httpx, pydantic, fastapi, etc.

# In Anaconda (for AI/ML training):
# - ML packages: tensorflow, pytorch, scikit-learn, etc.
```

### 3. Environment Branch Point

**Copy this EXACT test and see the result:**
```python
# Paste in your environment immediately:
import sys
import os

prefix = sys.prefix.lower()
env_type = "UNKNOWN"
if 'hermes' in prefix:
    env_type = "HERMES_SANDBOX (AI Agent Development)"
elif 'anaconda' in prefix or 'conda' in os.environ.get('CONDA_PREFIX', ''):
    env_type = "ANACONDA_USER (AI Training/GPU Work)"
elif 'site-packages' in prefix:
    env_type = "STANDARD_PYTHON_VENV"
else:
    # More detection
    python_path = sys.executable.lower()
    if 'appdata\local\hermes' in python_path:
        env_type = "HERMES_SANDBOX (relative path)"
    elif 'anaconda3' in python_path or 'c:\\users\\' in python_path:
        env_type = "WINDOWS_PYTHON (likely user environment)"

print(f"Environment type detected: {env_type}")
print(f"Prefix: {prefix}")
print(f"Executable: {sys.executable}")
```

### 4. Immediate Decision Matrix

**Based on environment type, take ONE path:**

#### **If HERMES_SANDBOX detected:**
```bash
# This is the Hermes AI agent environment
# ✓ Hermes project development
# ✗ NOT for your Anaconda/AI training work

# You should ask: "Why are you working in Hermes when I want to fix my Anaconda?"
# ❌ This is the wrong environment for your GPU training tasks
```

#### **If ANACONDA_USER detected:**
```bash
# This is your actual working environment for AI/ML training
# ✓ This is what you wanted me to fix!
# ✓ Has GPU packages, ML dependencies, training frameworks

# Run AI training commands HERE:
conda list
torch.cuda.is_available() if torch else "torch not installed"
```

#### **If UNCERTAIN:**
```bash
# Try these detection commands:

# Option A - Check specifically for conda:
conda info --envs --json 2>/dev/null

# Option B - Check for ML packages:
python -c "import pkgutil; print([name for finder, name, ispkg in pkgutil.iter_modules() if 'torch' in name or 'tensorflow' in name])"

# Option C - Check file paths:
ls "%USERPROFILE%\.conda\envs\" 2>/dev/null || ls "%USERPROFILE%\Anaconda3\envs\" 2>/dev/null || echo "No conda envs found"
```

### 5. Environment Verification Commands

```powershell
# Windows Environment Verification Commands:

# 1. Print exact path being used:
echo "%HOMEPATH%\%USERNAME%\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"
call "%HOMEPATH%\%USERNAME%\AppData\Local\hermes\hermes-agent\.venv\Scripts\activate.bat"

# 2. Check if you're in Hermes sandbox:
where python
python -c "import sys; print('Hermes sandbox:', 'hermes' in str(sys.prefix).lower())"

# 3. Check if you're in conda (good for AI training):
where conda
conda info --envs --json 2>/dev/null | findstr "envs"
```

### 6. Cross-Environment Comparison

| Feature | Hermes Sandbox | Anaconda User Environment |
|---------|----------------|---------------------------|
| **Purpose** | AI Agent development | AI Training/GPU work |
| **Packages** | Hermes tools, web APIs | ML frameworks, GPU libs |
| **Location** | `AppData\Local\hermes\hermes-agent\venv` | `C:\Users\valte\anaconda3` |
| **GPU Access** | ❌ No (Hermes is CPU-bound) | ✅ Yes (GPU-optimized) |
| **Usage** | Build Hermes tools, fix Hermes config | Train AI models, debug ML training |

## Immediate Action Required

**Choose your path RIGHT NOW:**

### **Path 1: If you're in the Hermes sandbox** (likely what happened):
1. Say: "I'm working in Hermes sandbox, NOT my Anaconda"
2. Explain: "I want to fix my Anaconda for GPU training, but can't access it"
3. Ask: "Should I work in your actual Anaconda environment instead?"

### **Path 2: If you're in Anaconda** (what you wanted):
1. Run the environment detection commands above
2. Share the output
3. Ask for guidance on fixing GPU setup
4. Tell me if you want me to handle the duplicate package cleanup

## Quick Environment Check Script

**Save this as `check_env.py` and run it:**
```python
import sys
import os
import subprocess

def check_environment():
    prefix = sys.prefix.lower()
    executable = sys.executable.lower()
    
    # Direct path detection
    if 'appdata\\local\\hermes' in executable:
        env_type = "HERMES_SANDBOX (wrong for training)"
    elif 'anaconda' in executable or 'conda' in os.environ.get('CONDA_PREFIX', ''):
        env_type = "ANACONDA_USER (correct for training)"
    elif 'site-packages' in prefix:
        env_type = "STANDARD_PYTHON_VENV (uncertain)"
    else:
        # Try to detect from python path
        if 'c:\\users\\' in executable:
            env_type = "WINDOWS_PYTHON (check manually)"
        else:
            env_type = "UNKNOWN - manual check needed"
    
    print("=== ENVIRONMENT DETECTION ===")
    print(f"Environment type: {env_type}")
    print(f"Python executable: {sys.executable}")
    print(f"Python prefix: {prefix}")
    
    if 'conda' in prefix or 'anaconda' in prefix:
        print("✅ Found conda/anaconda - good for AI training")
        try:
            import torch
            if torch.cuda.is_available():
                print("✅ GPU accessible - excellent for AI training")
            else:
                print("⚠️  GPU not available - install torch with CUDA support")
        except ImportError:
            print("⚠️  PyTorch not installed - install for GPU support")
    elif 'hermes' in prefix:
        print("❌ This is the HERMES AI agent environment")
        print("   - Wrong for your AI training tasks")
        print("   - Need to work in your actual Anaconda")
    
    return env_type

if __name__ == "__main__":
    env_type = check_environment()
```

## Decision Made Easily

**Copy this question for immediate clarification:**
```bash
# Run in your environment to get the answer
python -c "import sys; print('Hermes sandbox (wrong for training)?', 'hermes' in sys.prefix.lower())"
```

**Your answer to this question tells me exactly how to proceed:**
- **HERMES SANDBOX:** I work in Hermes, you're working in Anaconda (separate environments)
- **NOT HERMES SANDBOX:** I can work directly in your training environment

**Which environment are you actually in right now?**