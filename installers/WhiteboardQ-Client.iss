; WhiteboardQ Client Installer
; Inno Setup Script for the WhiteboardQ desktop client
;
; This installer:
; - Installs WhiteboardQ.exe to Program Files
; - Creates Start Menu shortcuts
; - Optionally adds Windows startup entry
; - Optionally creates desktop shortcut
;
; Build Requirements:
; - Inno Setup 6.x
; - dist/WhiteboardQ.exe must exist
;
; Build Command:
;   iscc WhiteboardQ-Client.iss

#define MyAppName "WhiteboardQ"
#define MyAppVersion GetStringFileInfo("..\dist\WhiteboardQ.exe", "ProductVersion")
#define MyAppPublisher "John Brantly"
#define MyAppURL "https://github.com/johnbrantly/whiteboardq"
#define MyAppExeName "WhiteboardQ.exe"

[Setup]
; Basic app info
AppId={{B2D4E6F8-1A3C-5E7G-9I1K-3M5O7Q9S1U3W}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Installation paths
DefaultDirName={autopf}\WhiteboardQ
DefaultGroupName=WhiteboardQ
DisableProgramGroupPage=yes

; Output settings
OutputDir=..\dist\installer
OutputBaseFilename=WhiteboardQ-Client-Setup
SetupIconFile=..\whiteboardq_client\resources\icon.ico
Compression=lzma
SolidCompression=yes

; Privileges - admin install recommended, but user can choose current-user only
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; UI settings
WizardStyle=modern
WizardSizePercent=100

; Uninstall settings
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
Name: "startupentry"; Description: "Start WhiteboardQ on Windows login"; GroupDescription: "Startup Options:"

[Files]
; Main executable
Source: "..\dist\WhiteboardQ.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start menu
Name: "{group}\WhiteboardQ"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall WhiteboardQ"; Filename: "{uninstallexe}"

; Desktop icon (optional)
Name: "{userdesktop}\WhiteboardQ"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Startup entry (optional) - runs on user login
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "WhiteboardQ"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startupentry

[Run]
; Optionally launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch WhiteboardQ"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up settings folder (optional - commented out to preserve settings)
; Uncomment to remove all settings on uninstall:
; Type: filesandordirs; Name: "{userappdata}\WhiteboardQ"

[Code]
var
  RemoveDataFiles: Boolean;

function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  // Stop any running instances before uninstall
  Exec('taskkill', '/IM WhiteboardQ.exe /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  // Ask user if they want to remove data files
  RemoveDataFiles := MsgBox('Do you want to remove all settings and log files?' + #13#10 + #13#10 +
    'Click Yes to remove all data, or No to keep your settings for future installations.',
    mbConfirmation, MB_YESNO) = IDYES;

  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and RemoveDataFiles then
  begin
    DelTree(ExpandConstant('{userappdata}\WhiteboardQ'), True, True, True);
  end;
end;

[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%nWhiteboardQ is a real-time message board for office communication.%n%nBefore installing, ensure you have the server address from your administrator.
