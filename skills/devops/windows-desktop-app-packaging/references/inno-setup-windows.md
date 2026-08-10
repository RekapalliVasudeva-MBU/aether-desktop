# Inno Setup installer recipe (Windows, safe bootloader)

## Critical rule
`Compression=lzma2` / `ultra64` makes the Inno **bootloader** crash on some
Windows machines with `0xc0000142 (STATUS_DLL_INIT_FAILED)`. Use `zip`.

## Minimal .iss (installer.iss)
```ini
[Setup]
AppName=Aether
AppVersion=1.0.1
DefaultDirName={localappdata}\Aether
DefaultGroupName=Aether
OutputDir=installer_out
OutputBaseFilename=Aether-Setup
SetupIconFile=logo.ico
Compression=zip
SolidCompression=no
PrivilegesRequired=lowest
WizardStyle=modern

[Files]
Source:"dist_build\Aether\*"; DestDir:"{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name:"{autodesktop}\Aether"; Filename:"{app}\Aether.exe"; WorkingDir:"{app}"
Name:"{group}\Aether"; Filename:"{app}\Aether.exe"; WorkingDir:"{app}"

[Run]
Filename:"{app}\Aether.exe"; Description:"Launch Aether"; Flags: nowait postinstall skipifsilent
```
- `{localappdata}` → `%LOCALAPPDATA%`, no admin needed.
- `PrivilegesRequired=lowest` avoids UAC prompt.
- Build: `iscc installer.iss` (Inno Setup 6).

## Alternative: self-extracting installer (no Inno)
If you compile your own boot with PyInstaller (`--onefile --windowed`) and
bundle a zlib payload, the payload MUST be the real onedir app folder, not the
installer exe (see SKILL.md "2-layer LOOP trap"). Verify the extracted dir has
`_internal/` + `Aether.exe`.
