[Setup]
AppName=TestInno
AppVersion=1.0
DefaultDirName={tmp}\testinno
OutputDir=.
OutputBaseFilename=test_installer
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "C:\Windows\System32\notepad.exe"; DestDir: "{app}"; Flags: ignoreversion
