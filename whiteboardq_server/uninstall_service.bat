@echo off
setlocal

:: WhiteboardQ Server - Windows Service Uninstaller

set SERVICE_NAME=WhiteboardQ

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

echo Stopping %SERVICE_NAME% service...
nssm stop %SERVICE_NAME% >nul 2>&1

echo Removing %SERVICE_NAME% service...
nssm remove %SERVICE_NAME% confirm
if %errorLevel% neq 0 (
    echo ERROR: Failed to remove service
    echo The service may not be installed
    pause
    exit /b 1
)

echo.
echo Service removed successfully!
echo.
echo Note: Log files in the logs\ directory were not deleted.
echo.
pause
