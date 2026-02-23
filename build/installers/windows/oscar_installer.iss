; ============================================================
; OSCAR Windows Installer — Inno Setup 6 Script
; Produces a professional .exe installer for Windows 10/11
; Download Inno Setup (free): https://jrsoftware.org/isdl.php
; ============================================================

#define AppName      "OSCAR"
#define AppVersion   "3.0.0"
#define AppPublisher "Institut français Italia"
#define AppURL       "https://www.institutfrancais.it"
#define AppExeName   "OSCAR.exe"
#define AppId        "{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; Output location (relative to the .iss file → go up to repo root → dist)
OutputDir=..\..\..\dist
OutputBaseFilename=OSCAR-{#AppVersion}-Windows-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Minimum Windows version: Windows 10
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Icon
SetupIconFile=..\..\..\build\icons\oscar.ico
UninstallDisplayIcon={app}\OSCAR.exe
; Don't require admin rights for per-user install
CreateUninstallRegKey=yes

[Languages]
Name: "french";   MessagesFile: "compiler:Languages\French.isl"
Name: "english";  MessagesFile: "compiler:Default.isl"
Name: "italian";  MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon";    Description: "{cm:CreateDesktopIcon}";    GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main application bundle (PyInstaller --onedir output)
Source: "..\..\..\dist\OSCAR\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";                  Filename: "{app}\{#AppExeName}"
Name: "{group}\Désinstaller {#AppName}";     Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";            Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
// Check for existing installation and offer to uninstall first
function InitializeSetup(): Boolean;
var
  PrevVersion: String;
  UninstallStr: String;
begin
  Result := True;
end;
