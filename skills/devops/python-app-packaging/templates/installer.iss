; installer.iss — Inno Setup 6 script for a normal Windows installer.
; Build:  iscc installer.iss   ->  installer_out/ProjectRAG-Setup.exe
; Per-user install (no admin required). App writes data to %LOCALAPPDATA%.

#define MyAppName "AetherMind Hybrid"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "AetherMind"
#define MyAppURL "https://marshy-ancient-rebuild.ngrok-free.dev/"
#define MyAppExe "AetherMindHybrid.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-A1B2-C3D4E5F6A7B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Per-user install -> no admin rights required (writes to %LOCALAPPDATA%)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
OutputDir=..\installer_out
OutputBaseFilename=ProjectRAG-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExe}
ArchitecturesInstallIn64BitMode=x64
UsedUserAreasWarning=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; The whole frozen PyInstaller bundle (AetherMindHybrid/ folder)
Source: "dist\AetherMindHybrid\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
// Check that Microsoft WebView2 Runtime is present (pywebview needs it).
function IsWebView2Installed(): Boolean;
var
  Installed: Boolean;
  Version: string;
begin
  Installed := RegQueryStringValue(HKLM,
    'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8EAF-99FEFD8DB94A}',
    'pv', Version) or
    RegQueryStringValue(HKCU,
    'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8EAF-99FEFD8DB94A}',
    'pv', Version);
  Result := Installed;
end;

procedure InitializeWizard();
begin
  if not IsWebView2Installed() then
  begin
    if MsgBox('AetherMind needs the Microsoft WebView2 Runtime (already on most Windows 10/11 PCs). ' +
             'Open the download page now?', mbConfirmation, MB_YESNO) = IDYES then
    begin
      ShellExec('open',
        'https://developer.microsoft.com/en-us/microsoft-edge/webview2/',
        '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
    end;
  end;
end;
