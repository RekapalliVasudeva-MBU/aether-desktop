# Windows installer crashes: 0xc0000142 / Inno 0xc0000005 — diagnosis & fix

Concrete recipe for the two failure modes that block a Python desktop app from
running on the end user's machine. Both happened on the Aether build and both
are now solved.

## Symptom A — `0xc0000142` "application was unable to start correctly"
Status `STATUS_DLL_INIT_FAILED`. On a VALID 64-bit PE (MZ header present,
`PE32+` / `0x20B`) this is almost always **antivirus blocking the runtime
temp-unpack**, NOT a missing VC++ redist.

Root cause: `--onefile` PyInstaller unpacks to `%TEMP%\_MEIxxxx` at every
launch; AV scans/quarantines the unpacked DLLs and the process dies before
`main()` runs. There is NO SideBySide / VC++ fault in the event log (that would
be a different, real missing-runtime error).

Fix:
1. Build `--onedir` (no runtime temp-unpack; files sit next to the exe).
2. Wrap the onedir folder in the installer (Inno / self-contained).
3. Verify the frozen exe launches and binds its port (`netstat -ano | grep :PORT`)
   BEFORE shipping.

## Symptom B — Inno Setup installer exits 1, no log, event log `0xc0000005`
The Inno bootloader itself access-violates when packaging a LARGE onedir folder
(thousands of files / torch bloat). A trivial Inno installer (one .exe) installs
fine; the full app folder crashes the bootloader.

Diagnosis steps:
- Run installer with `/VERYSILENT /DIR=<writable> /LOG=<path>` — if NO log file is
  created, the bootloader died before main.
- `wevtutil qe Application /c:30 /rd:true /f:text` → look for
  `Exception code: 0xc0000005` against `Aether-Setup.exe`.
- Sanity-check: build a trivial `.iss` that installs just `notepad.exe` — if THAT
  works, the payload (not Inno) is the problem.

Fix — try BOTH, in this order (on the Aether build, the compression change was
the actual fix; the ML exclusion only shrank the payload):

1. **Switch the Inno compression from LZMA2 to zip FIRST.** In the `.iss`, change
   `Compression=lzma2/ultra64` + `SolidCompression=yes`
   → `Compression=zip` + `SolidCompression=no`, then rebuild. On the Aether build
   this ALONE turned a 0xc0000005 crash into a clean install — the LZMA2/ultra64
   bootloader decompressor was what AV/Defender faulted on, NOT the file count.
   (lzma2/ultra64 is the Inno *default*, so if you left Compression unset, this
   is the most likely culprit.) Re-test the silent install
   (`/VERYSILENT /DIR=<writable>`) → confirm files land and the installed exe
   launches + binds its port before moving on.

2. **Shrink the payload by excluding unused heavy ML packages** (pulled in
   transitively by docling/huggingface hooks even though the app never imports
   them). Add to the PyInstaller command:
```   
--exclude-module torch --exclude-module torchvision --exclude-module torchaudio
--exclude-module transformers --exclude-module tokenizers --exclude-module safetensors
--exclude-module sentencepiece --exclude-module huggingface_hub --exclude-module timm
--exclude-module accelerate --exclude-module cv2 --exclude-module onnxruntime
```
Result on Aether: 921 MB → 135 MB (smaller + faster download). NOTE: excluding
these did NOT by itself clear the bootloader crash here — only the `zip`
compression did. But do both; the smaller payload is still worth it.
CRITICAL post-check: relaunch the frozen exe, hit `/api/config` AND run a real
RAG/docling query — confirm the exclusions didn't break a lazy `import torch`
hidden behind docling. If docling needs torch at runtime, keep `torch` and only
exclude the rest, or install torch in the build venv for bundling.

## Rebuild lock (`PermissionError: [WinError 5] Access is denied`)
A still-running `Aether.exe` (including a child PID) holds `dist/<AppName>` open,
so PyInstaller can't overwrite it → build aborts at COLLECT.
Fix: `taskkill /F /IM Aether.exe` (+ `Aether-Setup.exe`), confirm with `tasklist`,
then rebuild. If a dir is stuck as "Device or resource busy" (Windows deferred
delete), build to a fresh output dir (`dist_build/`) instead of forcing the delete.

## onedir vs onefile (decision)
- `--onedir`: robust against AV temp-unpack blocks; larger install folder; the
  installer copies the whole folder. PREFERRED for distribution.
- `--onefile`: single .exe but AV-flagged `_MEI` unpack → 0xc0000142 risk. Only if
  the user explicitly wants one file AND accepts a Defender exclusion.

## Verified Inno `.iss` essentials (per-user, no admin)
```
DefaultDirName={localappdata}\{#MyAppName}   ; no UAC / permission errors
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
CloseApplications=yes
[Files] Source: "dist_build\Aether\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
```
Install to `%LOCALAPPDATA%` (not Program Files) to avoid the permission/errno-13
class of failures entirely.
