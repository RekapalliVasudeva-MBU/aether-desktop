# Conda Environment Inspection on Windows

Reference for diagnosing conda environment and Jupyter kernel issues on Windows.

## Conda Not Found in Git-Bash

`conda` is not on PATH in MSYS/git-bash. Locate it:

```bash
# Common locations:
ls /c/ProgramData/anaconda3/Scripts/conda.exe     # system-wide install
ls /c/Users/<user>/anaconda3/Scripts/conda.exe     # user install
ls /c/Users/<user>/miniconda3/Scripts/conda.exe    # miniconda
```

Then use full path or export:
```bash
export PATH="/c/ProgramData/anaconda3/Scripts:/c/ProgramData/anaconda3/condabin:$PATH"
conda env list
```

## `base` Appears Twice in `conda env list`

**Cause:** Path casing mismatch — `C:\ProgramData\Anaconda3` vs `C:\ProgramData\anaconda3`. Windows treats these as the same path but conda's string comparison shows both.

**Confirm it's the same env:**
```bash
conda info --envs --json
```
Both entries will show `"name": "base"` — it's one environment, not two.

## Jupyter Shows More Kernels Than Exist

**Symptom:** JupyterLab kernel selector shows 4 entries but only 1-2 conda environments exist.

**Cause:** JupyterLab caches kernel display names from previous sessions. Old names like `Python [conda env:base-2]` or `Python [conda env:anaconda3-ai_env]` persist in the UI even after the underlying environment is renamed or removed.

**Diagnose real kernels:**
```bash
jupyter kernelspec list          # shows actual kernel specs on disk
jupyter kernelspec list --json   # machine-readable
```

**Kernel spec locations:**
- System: `<conda-prefix>/share/jupyter/kernels/`
- User: `~/AppData/Roaming/jupyter/kernels/`

**Rule:** If `jupyter kernelspec list` shows N kernels but JupyterLab shows M > N entries, the extra M-N entries are stale UI caches — not real environments. No deletion needed.

**To remove a real stale kernel:**
```bash
jupyter kernelspec remove <kernel-name>
```

**To clear JupyterLab UI cache:** Restart JupyterLab or clear browser localStorage for the Jupyter domain.

## Checking Environment Sizes

```bash
# Size of each conda environment
du -sh /c/ProgramData/anaconda3                    # base
du -sh /c/ProgramData/anaconda3/envs/ai_env       # ai_env
```

## When to Delete

Only delete a conda environment if:
1. It appears in `conda info --envs --json` as a real entry
2. It's not the `base` env (deleting base breaks conda)
3. You've confirmed no critical packages exist in it

```bash
conda env remove --name <env-name>
```
