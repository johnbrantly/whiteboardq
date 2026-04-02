@echo off
setlocal

:: WhiteboardQ Server - Windows Service Installer
:: Requires NSSM (https://nssm.cc/) to be installed and in PATH

set SERVICE_NAME=WhiteboardQ
set DISPLAY_NAME=WhiteboardQ Server
set DESCRIPTION=Real-time intra-office messaging queue server

:: Get the directory where this script is located
set SCRIPT_DIR=%~dp0
set EXE_PATH=%SCRIPT_DIR%dist\WhiteboardQ-Server.exe

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

:: Check if NSSM is available
where nssm >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: NSSM not found in PATH
    echo Download from https://nssm.cc/ and add to PATH
    pause
    exit /b 1
)

:: Check if executable exists
if not exist "%EXE_PATH%" (
    echo ERROR: WhiteboardQ-Server.exe not found at:
    echo %EXE_PATH%
    echo Build the server first with: pyinstaller whiteboardq_server.spec
    pause
    exit /b 1
)

:: Create logs directory
if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs"

echo Installing %SERVICE_NAME% service...

:: Install the service
nssm install %SERVICE_NAME% "%EXE_PATH%"
if %errorLevel% neq 0 (
    echo ERROR: Failed to install service
    pause
    exit /b 1
)

:: Configure service settings
nssm set %SERVICE_NAME% DisplayName "%DISPLAY_NAME%"
nssm set %SERVICE_NAME% Description "%DESCRIPTION%"
nssm set %SERVICE_NAME% AppDirectory "%SCRIPT_DIR%"
nssm set %SERVICE_NAME% Start SERVICE_AUTO_START

:: Configure logging
nssm set %SERVICE_NAME% AppStdout "%SCRIPT_DIR%logs\stdout.log"
nssm set %SERVICE_NAME% AppStderr "%SCRIPT_DIR%logs\stderr.log"
nssm set %SERVICE_NAME% AppRotateFiles 1
nssm set %SERVICE_NAME% AppRotateBytes 1048576

:: Start the service
echo Starting %SERVICE_NAME% service...
nssm start %SERVICE_NAME%

echo.
echo Service installed successfully!
echo.
echo The service will:
echo - Start automatically on boot
echo - Log to %SCRIPT_DIR%logs\
echo - Listen on https://localhost:5000 (TLS enabled)
echo.
echo To manage the service:
echo   nssm status %SERVICE_NAME%
echo   nssm stop %SERVICE_NAME%
echo   nssm start %SERVICE_NAME%
echo   nssm restart %SERVICE_NAME%
echo.
pause
