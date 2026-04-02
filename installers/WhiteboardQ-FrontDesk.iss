; WhiteboardQ Front Desk Installer
; Inno Setup Script for the Front Desk deployment scenario
;
; This installer:
; - Installs WhiteboardQ Server Manager to Program Files
; - Creates data directory in ProgramData
; - Adds Windows startup entry (runs in tray mode)
; - Adds firewall rule for port 5000
;
; Build Requirements:
; - Inno Setup 6.x
; - dist/WhiteboardQ-Server.exe and dist/WhiteboardQ-FrontDesk-Manager.exe must exist
;
; Build Command:
;   iscc WhiteboardQ-FrontDesk.iss

#define MyAppName "WhiteboardQ Server (FrontDesk)"
#define MyAppVersion GetStringFileInfo("..\dist\WhiteboardQ-FrontDesk-Manager.exe", "ProductVersion")
#define MyAppPublisher "John Brantly"
#define MyAppURL "https://github.com/johnbrantly/whiteboardq"
#define MyAppExeName "WhiteboardQ-FrontDesk-Manager.exe"

[Setup]
; Basic app info
AppId={{FCF1C84D-C41A-4BE8-9498-83FFA72E7D6F}
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
OutputBaseFilename=WhiteboardQ-FrontDesk-Server-Setup
SetupIconFile=..\whiteboardq_server\resources\icon.ico
Compression=lzma
SolidCompression=yes

; Privileges (requires admin for firewall rules, Program Files, and ProgramData setup)
PrivilegesRequired=admin

; UI settings
WizardStyle=modern
WizardSizePercent=100

; Info page shown before installation (firewall notice)
InfoBeforeFile=InfoBefore.txt

; Uninstall settings
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startupentry"; Description: "Start WhiteboardQ Server on Windows login (recommended)"; GroupDescription: "Startup Options:"
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
; Main executables
Source: "..\dist\WhiteboardQ-FrontDesk-Manager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\WhiteboardQ-Server.exe"; DestDir: "{app}"; Flags: ignoreversion

; Note: Additional files may be needed depending on PyInstaller output mode
; If using --onedir instead of --onefile, add:
; Source: "..\dist\WhiteboardQ-FrontDesk-Manager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; Create data directories per spec: %ProgramData%\WhiteboardQ\
; Contains: config.json, whiteboardq.db, logs/server.log
Name: "{commonappdata}\WhiteboardQ"; Permissions: users-modify
Name: "{commonappdata}\WhiteboardQ\logs"; Permissions: users-modify
Name: "{commonappdata}\WhiteboardQ\certs"; Permissions: users-modify

[Icons]
; Start menu - no --tray so clicking shows the manager window
Name: "{group}\WhiteboardQ Server Manager"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall WhiteboardQ Server"; Filename: "{uninstallexe}"

; Desktop icon (optional) - no --tray so clicking shows the manager window
Name: "{commondesktop}\WhiteboardQ Server Manager"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Startup entry - FrontDesk Manager starts with tray behavior built-in
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "WhiteboardQServer"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startupentry

[Run]
; Add firewall rules (runs as admin since we require it)
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""WhiteboardQ Server"" dir=in action=allow protocol=TCP localport=5000"; Flags: runhidden; StatusMsg: "Opening TCP port 5000 in Windows Firewall..."
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""WhiteboardQ Discovery"" dir=in action=allow protocol=UDP localport=5001"; Flags: runhidden; StatusMsg: "Opening UDP port 5001 for discovery..."

; Optionally launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch WhiteboardQ Server"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Remove firewall rules on uninstall (RunOnceId ensures this only runs once)
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""WhiteboardQ Server"""; Flags: runhidden; RunOnceId: "RemoveFirewallRule"
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""WhiteboardQ Discovery"""; Flags: runhidden; RunOnceId: "RemoveDiscoveryRule"

[UninstallDelete]
; Clean up data files (optional - commented out to preserve data)
; Uncomment the following lines to remove all data on uninstall:
; Type: filesandordirs; Name: "{commonappdata}\WhiteboardQ"

[Code]
var
  RemoveDataFiles: Boolean;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Any post-installation tasks can go here
  end;
end;

function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  // Stop any running instances before uninstall
  Exec('taskkill', '/IM WhiteboardQ-Server.exe /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('taskkill', '/IM WhiteboardQ-FrontDesk-Manager.exe /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  // Ask user if they want to remove data files
  RemoveDataFiles := MsgBox('Do you want to remove all server data files?' + #13#10 + #13#10 +
    'This includes the database, logs, and certificates.' + #13#10 + #13#10 +
    'Click Yes to remove all data, or No to keep them for future installations.',
    mbConfirmation, MB_YESNO) = IDYES;

  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and RemoveDataFiles then
  begin
    DelTree(ExpandConstant('{commonappdata}\WhiteboardQ'), True, True, True);
  end;
end;

[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%nWhiteboardQ Server is a real-time message queue for office communication.%n%nThis Front Desk installation will:%n- Install the server and manager to Program Files%n- Optionally start the server automatically on Windows login%n- Configure Windows Firewall (details on next page)
