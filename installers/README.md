# WhiteboardQ Installers

This directory contains Inno Setup scripts for creating Windows installers.

## Prerequisites

1. **Inno Setup 6.x** - Download from https://jrsoftware.org/isinfo.php
2. **Built executables** - Run `python build.py` from project root first

## Available Installers

### WhiteboardQ-FrontDesk.iss

**Purpose:** Front Desk deployment scenario - server runs on a workstation with system tray integration.

**Features:**
- Installs Server and Server Manager to `%ProgramFiles%\WhiteboardQ\`
- Creates data directories in `%ProgramData%\WhiteboardQ\`
- Optionally adds startup registry entry (runs `--tray` mode on login)
- Adds Windows Firewall rule for port 5000 (TCP, private/domain profiles)
- Creates Start Menu shortcuts
- Clean uninstall (removes firewall rule, registry entry)

**Build Command:**
```powershell
cd installers
iscc WhiteboardQ-FrontDesk.iss
```

**Output:** `dist/installer/WhiteboardQ-FrontDesk-Setup.exe`

## Directory Structure After Install

```
%ProgramFiles%\WhiteboardQ\
├── WhiteboardQ-Server.exe
└── WhiteboardQ-Server-Manager.exe

%ProgramData%\WhiteboardQ\
├── data\
│   └── whiteboard.db
├── logs\
│   └── server.log
└── certs\
    └── (TLS certificates)
```

## Startup Behavior

When "Start WhiteboardQ Server on Windows login" is selected during install:
- Registry entry added: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\WhiteboardQServer`
- Value: `"C:\Program Files\WhiteboardQ\WhiteboardQ-Server-Manager.exe" --tray`
- Server Manager starts minimized to system tray
- Server auto-starts (hidden, no console window)
- User can interact via tray icon context menu

## Firewall Rule

The installer creates a firewall rule allowing inbound TCP connections on port 5000 for private and domain network profiles (not public). This allows clients on the same network to connect to the server.

Rule name: "WhiteboardQ Server"

## Silent Install

For unattended deployment:
```powershell
WhiteboardQ-FrontDesk-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /TASKS="startupentry"
```

## Customization

To modify the installer:
1. Edit the `.iss` file
2. Update `MyAppVersion` for version changes
3. Rebuild with `iscc`

## Notes

- The installer requires admin privileges for:
  - Writing to Program Files
  - Creating firewall rules
- Data files are stored in ProgramData (not Program Files) for proper permissions
- Uninstall preserves data files by default (uncomment `[UninstallDelete]` section to remove)
