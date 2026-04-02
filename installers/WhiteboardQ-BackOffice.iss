; WhiteboardQ BackOffice Server Installer
; Inno Setup Script for the IT Server / BackOffice deployment scenario
;
; This installer:
; - Installs WhiteboardQ Server (as Windows Service) and Server Manager to Program Files
; - Creates data directory in ProgramData
; - Registers and starts the Windows Service
; - Adds firewall rule for port 5000
;
; Build Requirements:
; - Inno Setup 6.x
; - dist/WhiteboardQ-Server-Service.exe and dist/WhiteboardQ-BackOffice-Manager.exe must exist
;
; Build Command:
;   iscc WhiteboardQ-BackOffice.iss

#define MyAppName "WhiteboardQ Server (BackOffice)"
#define MyAppVersion GetStringFileInfo("..\dist\WhiteboardQ-BackOffice-Manager.exe", "ProductVersion")
#define MyAppPublisher "John Brantly"
#define MyAppURL "https://github.com/johnbrantly/whiteboardq"
#define MyAppExeName "WhiteboardQ-BackOffice-Manager.exe"

[Setup]
; Basic app info - DIFFERENT GUID from FrontDesk to allow both to be installed
AppId={{A7E2B5C1-8D4F-4A9E-B6C3-1F2D3E4A5B6C}
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
OutputBaseFilename=WhiteboardQ-BackOffice-Server-Setup
SetupIconFile=..\whiteboardq_server\resources\icon.ico
Compression=lzma
SolidCompression=yes

; Privileges (requires admin for service registration and Program Files)
PrivilegesRequired=admin

; UI settings
WizardStyle=modern
WizardSizePercent=100

; Info page shown before installation (firewall + service notice)
InfoBeforeFile=InfoBefore-BackOffice.txt

; Uninstall settings
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} (BackOffice)

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
; Main executables
Source: "..\dist\WhiteboardQ-BackOffice-Manager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\WhiteboardQ-Server-Service.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; Create data directories per spec: %ProgramData%\WhiteboardQ\
; Contains: config.json, whiteboardq.db, logs/server.log
Name: "{commonappdata}\WhiteboardQ"; Permissions: users-modify
Name: "{commonappdata}\WhiteboardQ\logs"; Permissions: users-modify
Name: "{commonappdata}\WhiteboardQ\certs"; Permissions: users-modify

[Icons]
; Start menu
Name: "{group}\WhiteboardQ Server Manager"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall WhiteboardQ Server"; Filename: "{uninstallexe}"

; Desktop icon (optional)
Name: "{commondesktop}\WhiteboardQ Server Manager"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Add firewall rules (runs as admin since we require it)
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""WhiteboardQ Server"" dir=in action=allow protocol=TCP localport=5000"; Flags: runhidden; StatusMsg: "Opening TCP port 5000 in Windows Firewall..."
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""WhiteboardQ Discovery"" dir=in action=allow protocol=UDP localport=5001"; Flags: runhidden; StatusMsg: "Opening UDP port 5001 for discovery..."

; Install the Windows Service
Filename: "{app}\WhiteboardQ-Server-Service.exe"; Parameters: "install"; Flags: runhidden; StatusMsg: "Installing WhiteboardQ Server service..."

; Set service to auto-start
Filename: "sc"; Parameters: "config WhiteboardQServer start= auto"; Flags: runhidden; StatusMsg: "Configuring service auto-start..."

; Start the service
Filename: "sc"; Parameters: "start WhiteboardQServer"; Flags: runhidden; StatusMsg: "Starting WhiteboardQ Server service..."

; Optionally launch Server Manager after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch WhiteboardQ Server Manager"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Stop the service first
Filename: "sc"; Parameters: "stop WhiteboardQServer"; Flags: runhidden; RunOnceId: "StopService"

; Wait a moment for service to stop
Filename: "timeout"; Parameters: "/t 2 /nobreak"; Flags: runhidden; RunOnceId: "WaitForStop"

; Remove the service
Filename: "{app}\WhiteboardQ-Server-Service.exe"; Parameters: "remove"; Flags: runhidden; RunOnceId: "RemoveService"

; Remove firewall rules on uninstall
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""WhiteboardQ Server"""; Flags: runhidden; RunOnceId: "RemoveFirewallRule"
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""WhiteboardQ Discovery"""; Flags: runhidden; RunOnceId: "RemoveDiscoveryRule"

[UninstallDelete]
; Clean up data files (optional - commented out to preserve data)
; Uncomment the following lines to remove all data on uninstall:
; Type: filesandordirs; Name: "{commonappdata}\WhiteboardQ"

[Code]
var
  RemoveDataFiles: Boolean;

function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  // Check if WhiteboardQ service is already running and stop it
  Exec('sc', 'stop WhiteboardQServer', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;

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
  // Stop the service before uninstall
  Exec('sc', 'stop WhiteboardQServer', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  // Stop any running Manager instances
  Exec('taskkill', '/IM WhiteboardQ-BackOffice-Manager.exe /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

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
WelcomeLabel2=This will install [name/ver] on your computer.%n%nWhiteboardQ Server is a real-time message queue for office communication.%n%nThis BackOffice installation will:%n- Install the server as a Windows Service (auto-starts on boot)%n- Install the Server Manager to Program Files%n- Configure Windows Firewall (details on next page)
