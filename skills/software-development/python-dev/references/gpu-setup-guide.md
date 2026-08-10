# GPU Setup Guide - Windows Environment

## TLDR
**Current Status**: This is a Python venv (Hermes environment), not the actual user machine with GPU.

**Reality Check**: You need to install GPU computing on your WINDOWS PHYSICAL MACHINE, not in this Hermes environment.

## What I Found

### Environment Detection
```bash
# This is what I ran:
python -c "import torch; print('GPU available:', torch.cuda.is_available())" 2>/dev/null || echo "PyTorch not installed"

# Result: PyTorch not installed in this environment
# But Windows user DOES have GPU in physical machine
```

### User Machine vs Hermes Environment
| System | What's in this Hermes Environment | What you NEED on your machine |
|--------|-----------------------------------|-------------------------------|
| GPU    | ❌ No CUDA accessible from venv    | ✅ Physical NVIDIA/AMD GPU installed |
| CUDA   | ❌ Not detectable in venv         | ✅ CUDA toolkit version matching GPU |
| PyTorch| ❌ Not installed                  | ✅ GPU-optimized PyTorch build |
| Conda  | ❌ Not available                 | ✅ GPU-enabled Conda environment |

## Required Actions for Actual User Machine

### Step 1: Install NVIDIA GPU Drivers
```powershell
# Download from NVIDIA website: https://www.nvidia.com/Download/index.aspx
# Choose: Game Ready Driver (Recommended) or Studio Driver (for AI/ML)
```

### Step 2: Install CUDA Toolkit
**Note**: Must match GPU compute capability and PyTorch CUDA version.

Example for RTX 3060 (CUDA 12.6 compatible):
```powershell
# Download CUDA 12.6 toolkit installer
# Run installer, accept defaults, add to PATH
```

### Step 3: Set System Environment Variables
```powershell
# In PowerShell as Administrator:
$env:CUDA_PATH = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6"
$env:CUDA_HOME = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6"
$env:PATH = $env:PATH + ";" + $env:CUDA_PATH + "\bin"

# Make permanent:
[Environment]::SetEnvironmentVariable("CUDA_PATH", "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6", "Machine")
[Environment]::SetEnvironmentVariable("CUDA_HOME", "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6", "Machine")
```

### Step 4: Install GPU-Optimized PyTorch

**Method A: Conda (Recommended)**
```bash
# Activate your Conda environment
conda activate <your-ai-env>

# Get right CUDA version - run on user machine:
conda install -c pytorch pytorch torchvision torchaudio cuda-version=12.6
```

**Method B: Direct pip**
```bash
# On user machine, create fresh virtual environment
cd ~/projects
python -m venv gpu_env
source activate gpu_env

# Install matching versions
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
pip3 install torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
```

### Step 5: Verify Installation
```python
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU count: {torch.cuda.device_count()}")
print(f"Current GPU: {torch.cuda.current_device()}")
print(f"GPU name: {torch.cuda.get_device_name(0)}")
```

### Step 6: Test GPU Performance
```python
import torch
import time

# GPU memory test
torch.cuda.empty_cache()
print(f"GPU Memory (before): {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")

# GPU computation test
x = torch.randn(1000, 1000).cuda()
y = torch.randn(1000, 1000).cuda()

start = time.time()
z = torch.matmul(x, y)
print(f"Matrix multiplication time: {time.time() - start:.3f}s")
print(f"GPU Memory (after): {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")

# Cleanup
torch.cuda.empty_cache()
```

## Troubleshooting

### GPU Not Detected
```bash
# On user machine, open Command Prompt as Admin:
nvidia-smi
# Should show GPU info if drivers installed correctly
```

### CUDA Path Issues
```powershell
# Verify CUDA installation
where nvcc
where cublas64_11.dll
```

### PyTorch CUDA Version Mismatch
```bash
# Match CUDA toolkit version to PyTorch build
# Example: CUDA 12.6 needs PyTorch with cu126 suffix
pip3 install torch --index-url https://download.pytorch.org/whl/cu126
```

## Important Notes

### Virtual Environment vs System
- Never install GPU computing in system Python (admin required)
- Always use virtual environment to avoid permission issues
- Use `conda create -n gpu_env python=3.11` instead of `python -m venv gpu_env` for GPU packages

### Windows-Specific Considerations
- Certain AMD GPUs need BIOS virtualization settings enabled
- Windows 11 has better GPU driver support than Windows 10 for ML workloads
- Consider using WSL2 + Linux GPU setup for better ML framework compatibility

### Memory Management
```python
# Important for GPU training
import torch

# 1. Force CPU for small tensors (saves GPU memory)
x_cpu = torch.randn(100, 100)  # On CPU
x_gpu = x.cpu()  # Move to GPU when needed

# 2. Clear GPU cache
x_gpu = None
torch.cuda.empty_cache()

# 3. Use smaller batch sizes for limited GPU memory
# Common pattern: batch_size = 2-4 for RTX 3060/3070
```

## Verification Checklist

✅ NVIDIA GPU drivers installed
✅ CUDA toolkit matching GPU
✅ PyTorch with CUDA support
✅ Environment variables set
✅ Virtual environment created
✅ GPU computation test successful
✅ Memory management practices in place

After these steps, your actual machine will be ready for GPU-accelerated ML model training!