# WhiteboardQ Full Build Script
# Builds all executables and installers

$ErrorActionPreference = "Stop"
$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "WhiteboardQ Full Build" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Step 1: Build executables
Write-Host "Building executables..." -ForegroundColor Yellow
python build.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nBuild failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n----------------------------------------" -ForegroundColor Gray

# Step 2: Build installers
$installers = @(
    "installers\WhiteboardQ-FrontDesk.iss",
    "installers\WhiteboardQ-BackOffice.iss",
    "installers\WhiteboardQ-Client.iss"
)

foreach ($iss in $installers) {
    Write-Host "`nBuilding $iss..." -ForegroundColor Yellow
    & $iscc $iss
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`nInstaller build failed: $iss" -ForegroundColor Red
        exit 1
    }
}

# Done
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "BUILD COMPLETE" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Executables:" -ForegroundColor Cyan
Get-ChildItem dist\*.exe | ForEach-Object {
    $size = [math]::Round($_.Length / 1MB, 1)
    Write-Host "  $($_.Name) ($size MB)"
}

Write-Host "`nInstallers:" -ForegroundColor Cyan
Get-ChildItem dist\installer\*.exe | ForEach-Object {
    $size = [math]::Round($_.Length / 1MB, 1)
    Write-Host "  $($_.Name) ($size MB)"
}

Write-Host ""
