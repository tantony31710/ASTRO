# ASTRO Desktop App — standalone Windows .exe builder.
#
# One-command packaging:
#   .\build_exe.ps1            # builds ASTRO.exe in dist\
#   .\build_exe.ps1 -Installer # additionally bundles an Inno Setup installer (if installed)
#
# Requires:
#   pip install pyinstaller
#   (optional) Inno Setup from https://jrsoftware.org/isinfo.php
#
# The resulting ASTRO.exe carries the Python runtime, customtkinter, the
# voice stack, and the JARVIS brain inside one file. Your .env, model
# weights, and media cache stay external (they're next to the exe or in the
# install folder) so you can reconfigure without rebuilding.
#
# Run from the ASTRO repo root in PowerShell:
#   .\build_exe.ps1
# The exe lands in .\dist\ASTRO.exe. Keep the repo folder structure intact
# when you deploy (gui_app.exe next to my_large_data_vault/).

param([switch]$Installer)

$ErrorActionPreference = "Stop"

Write-Host "=== ASTRO desktop exe builder ===" -ForegroundColor Cyan

# 1. Ensure pyinstaller is available
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    pip install -q pyinstaller
}

# 2. Build a single-folder exe (more reliable than --onefile with customtkinter)
#    --windowed hides the console; --add-data bundles the vault so the exe
#    finds the brain and voice modules via __file__ resolution.
pyinstaller `
    --noconfirm `
    --windowed `
    --name ASTRO `
    --add-data "my_large_data_vault;my_large_data_vault" `
    --collect-all customtkinter `
    --hidden-import=dotenv `
    --hidden-import=speech_recognition `
    --hidden-import=pystray `
    --hidden-import=PIL `
    gui_app.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed — see output above."
    exit 1
}

Write-Host "Build complete: .\dist\ASTRO\ASTRO.exe" -ForegroundColor Green

# 3. Make sure the bundled vault's .env.example is visible for first run
$bundleEnv = "dist\ASTRO\_internal\my_large_data_vault\.env"
if (-not (Test-Path $bundleEnv)) {
    Copy-Item "my_large_data_vault\.env.example" $bundleEnv -ErrorAction SilentlyContinue
    Write-Host "Seeded .env from .env.example in the bundle." -ForegroundColor Yellow
}

# 4. (Optional) Inno Setup installer that also registers autostart + NSSM service
if ($Installer) {
    $inno = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if (-not (Test-Path $inno)) {
        Write-Host "Inno Setup not found — install it from https://jrsoftware.org/isinfo.php" -ForegroundColor Yellow
        Write-Host "Skipping installer generation. You can still run dist\ASTRO\ASTRO.exe directly." -ForegroundColor Yellow
    } else {
        Write-Host "Building installer (ASTRO_Setup.exe)..." -ForegroundColor Yellow
        & $inno setup_inno.iss
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Installer ready: Output\ASTRO_Setup.exe" -ForegroundColor Green
        }
    }
}

Write-Host ""
Write-Host "Deploy note: copy the whole dist\ASTRO folder (exe + _internal)." -ForegroundColor Cyan
Write-Host "Then: git pull on the repo is NOT needed — the exe is self-contained."
