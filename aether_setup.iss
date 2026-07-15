; Aether Desktop — Inno Setup installer script
; Builds a proper 64-bit Windows installer that extracts the PyInstaller
; --onedir app (dist/Aether/*) to the user's LocalAppData (no admin needed,
; no UAC prompt, no runtime temp-unpack that AV blocks).

#define MyAppName "Aether"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "AetherMind"
#define MyAppURL "https://github.com/RekapalliVasudeva-MBU/aether-desktop"
#define MyAppExeName "Aether.exe"

[Setup]
AppId={{8E3C9A1B-2F4D-4C8E-9B6A-1D7E5C3F9A02}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
; Per-user, no admin: install under LocalAppData so no UAC / permission errors.
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Allow non-admin install location too:
DirExistsWarning=no
DisableDirPage=auto
OutputDir=dist
OutputBaseFilename=Aether-Setup
SetupIconFile=desktop_ui\logo.ico
Compression=zip
SolidCompression=no
WizardStyle=modern
; Architecture: require 64-bit Windows (our build is AMD64).
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
; Close any running Aether before overwriting files.
CloseApplications=yes
CloseApplicationsFilter=*.exe
RestartApplications=no
UninstallDisplayName={#MyAppName}
; Add to "Programs and Features"
CreateUninstallRegKey=yes
; Windows 10+ target
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; The entire PyInstaller --onedir output.
Source: "dist_build\Aether\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; RAG PDF drop-in folder (so the user can paste PDFs right after install)
Name: "{localappdata}\Aether\rag_pdfs"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\logo.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\logo.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
