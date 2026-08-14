# ASTRO GUI app — Windows background service (NSSM-based).
#
# Difference from the headless service_jarvis.ps1: this one launches the
# GUI window (or the packaged exe) as a user-session process registered
# with NSSM, so it survives your manual closes and restarts on boot.
#
# Usage (Admin PowerShell, from the ASTRO repo root):
#   .\service_gui.ps1 install            # register + start
#   .\service_gui.ps1 install -Exe       # if you built the exe via build_exe.ps1
#   .\service_gui.ps1 status             # running?
#   .\service_gui.ps1 uninstall          # stop + remove
#
# Requires NSSM:  winget install nssm.nssm
#
# Note: GUI services interact with the desktop only when someone is logged
# in. For pure login-autostart without NSSM, prefer the startup shortcut
# from setup_jarvis.ps1 (or the Inno Setup installer's autostart task).

param(
    [ValidateSet("install", "status", "uninstall")]$Action = "install",
    [switch]$Exe
)

$ErrorActionPreference = "Stop"
$repoRoot = (Get-Location).Path
$serviceName = "ASTRO-GUI"

# Resolve the vault folder regardless of its name (underscore = current,
# hyphen = legacy) so a repo rename never breaks registration.
$vaultFolder = "my_large_data_vault"
if (-not (Test-Path (Join-Path $repoRoot $vaultFolder))) {
    $vaultFolder = "my-large-data-vault"
}

if ($Exe) {
    $binary = Join-Path $repoRoot "dist\ASTRO\ASTRO.exe"
    if (-not (Test-Path $binary)) {
        Write-Error "dist\ASTRO\ASTRO.exe not found — run .\build_exe.ps1 first."
        exit 1
    }
    $launchCmd = $binary
    $launchDir = Join-Path $repoRoot "dist\ASTRO"
} else {
    $pythonw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
    if (-not $pythonw) {
        Write-Error "pythonw not found — run setup_jarvis.ps1 (or install Python) first."
        exit 1
    }
    $launchCmd = $pythonw
    $launchDir = $repoRoot
}
$scriptPath = Join-Path $repoRoot "gui_app.py"

$nssm = (Get-Command nssm -ErrorAction SilentlyContinue).Source
if (-not $nssm) {
    Write-Error "nssm not found — install it: winget install nssm.nssm"
    exit 1
}

switch ($Action) {
    "install" {
        & $nssm install $serviceName $launchCmd $scriptPath
        & $nssm set $serviceName AppDirectory $launchDir
        & $nssm set $serviceName DisplayName "ASTRO — Local AI Desktop"
        & $nssm set $serviceName Description "Always-on ASTRO assistant GUI (wake word + voice)"
        & $nssm set $serviceName AppExit Default Restart
        & $nssm set $serviceName AppRestartDelay 5000
        & $nssm set $serviceName AppStdout (Join-Path $repoRoot "astro_gui_service.log")
        & $nssm set $serviceName AppStderr (Join-Path $repoRoot "astro_gui_service_err.log")
        & net start $serviceName
        Write-Host "Service '$serviceName' installed and started. Check services.msc." -ForegroundColor Green
        Write-Host "Log: .\astro_gui_service.log" -ForegroundColor Gray
    }
    "status" {
        Get-Service $serviceName -ErrorAction SilentlyContinue |
            Format-Table Name, Status, StartType -AutoSize
    }
    "uninstall" {
        Stop-Service $serviceName -Force -ErrorAction SilentlyContinue
        & $nssm remove $serviceName confirm
        Write-Host "Service '$serviceName' removed." -ForegroundColor Green
    }
}
