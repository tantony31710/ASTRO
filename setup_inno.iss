; ASTRO — Local AI Desktop installer (Inno Setup)
;
; Run via: build_exe.ps1 -Installer
; Prerequisite: PyInstaller output in dist\ASTRO\
;
; The installer:
;   - installs ASTRO.exe (with its bundled vault) to Program Files\ASTRO
;   - copies your .env into the install folder if not already there
;   - creates a Start Menu shortcut and an optional desktop shortcut
;   - offers to register ASTRO at Windows startup (login autostart)

#define MyAppName "ASTRO — Local AI Desktop"
#define MyAppVersion "1.0"
#define MyAppPublisher "ASTRO"
#define MyAppExeName "ASTRO.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\ASTRO
DefaultGroupName=ASTRO
AllowNoIcons=yes
LicenseFile=
OutputDir=Output
OutputBaseFilename=ASTRO_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallModeIn64Mode=x64

[Files]
Source: "dist\ASTRO\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ASTRO"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\ASTRO"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"
Name: "autostart"; Description: "Start ASTRO automatically when &I log in (recommended)"

[Registry]
Root: HKCU; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "ASTRO"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch ASTRO now"; Flags: nowait postinstall skipifsilent
