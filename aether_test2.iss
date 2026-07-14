[Setup]
AppName=AetherTest
AppVersion=1.0.0
DefaultDirName={localappdata}\AetherTest
OutputDir=.
OutputBaseFilename=aether_test2
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
CloseApplications=no

[Files]
Source: "dist\Aether\Aether.exe"; DestDir: "{app}"; Flags: ignoreversion
