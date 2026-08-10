# Common Software Leftover Patterns on Windows

## After Uninstalling Software — Where Leftovers Hide

### MATLAB
After uninstalling MATLAB, check these:
- `C:\Program Files\MATLAB\R20XXx\` — main install, **needs admin** to delete
- `C:\Users\<user>\AppData\Local\MathWorks\` — 1+ GB of caches, **needs admin**
- `C:\Users\<user>\AppData\Roaming\MathWorks\` — small, user-space
- `C:\Users\<user>\Downloads\matlab_R20XXx_Windows.exe` — installer EXE, 250+ MB each
- `C:\Users\<user>\Downloads\_temp_matlab_R20XXx_Windows\` — extracted installer, 400-600 MB

### Adobe
- `C:\Program Files\Common Files\Adobe\Adobe Media Encoder\` — **needs admin**
- `C:\Program Files\Common Files\Adobe\UXP\` — **needs admin**
- `C:\Users\<user>\AppData\Roaming\Adobe\` — user-space, safe to delete
- `C:\Users\<user>\AppData\Roaming\com.adobe.dunamis\` — 170 MB cache
- `C:\Users\<user>\AppData\Local\Adobe\` — small caches
- `C:\Users\<user>\AppData\LocalLow\Adobe\` — 50+ MB

### npm / Node.js
- `C:\Users\<user>\AppData\Local\npm-cache\` — can be 2+ GB, safe to nuke entirely

### Thumbnail Cache
- `C:\Users\<user>\AppData\Local\Microsoft\Windows\Explorer\thumbcache_*.db` — 300-400 MB
- `C:\Users\<user>\AppData\Local\Microsoft\Windows\Explorer\iconcache_*.db` — 100 MB
- Windows rebuilds these automatically

### Temp Installers in Downloads
- `Downloads\*.exe` — installers (check if app already installed)
- `Downloads\_temp_*` — extracted installer folders
- `AppData\Local\Temp\WinGet\` — Windows Package Manager downloads

### System Junk
- `C:\$Recycle.Bin\` — recycle bin
- `C:\$Windows.~WS\` — Windows upgrade staging, **needs admin**
- `C:\Users\<user>\AppData\Local\Microsoft\Windows\WebCache\` — 50-60 MB
