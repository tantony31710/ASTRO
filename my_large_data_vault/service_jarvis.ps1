# JARVIS as a genuine Windows Service (NSSM-based).
#
# A real service restarts automatically on crash, survives user logout
# (if configured), and shows up in services.msc. Requires NSSM:
#   winget install nssm.nssm
#
# Usage (Admin PowerShell, from the ASTRO repo root):
#   .\my-large-data-vault\service_jarvis.ps1 install   # register + start
#   .\my-large-data-vault\service_jarvis.ps1 status    # running?
#   .\my-large-data-vault\service_jarvis.ps1 uninstall # stop + remove
#
# Note: a headless pythonw service has no tray icon — that's the trade-off
# for always-on reliability. For a tray icon at login, use setup_jarvis.ps1's
# startup shortcut instead (or both: service for the API, shortcut for tray).

param([ValidateSet("install", "status", "uninstall")]$Action = "install")

$repoRoot = (Get-Location).Path
$scriptPath = Join-Path $repoRoot "my-large-data-vault\tray_jarvis.pyw"
$serviceName = "JARVIS"

$pythonw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $pythonw) {
    Write-Error "pythonw not found — run setup_jarvis.ps1 first."
    exit 1
}
$nssm = (Get-Command nssm -ErrorAction SilentlyContinue).Source
if (-not $nssm) {
    Write-Error "nssm not found — install it: winget install nssm.nssm"
    exit 1
}

switch ($Action) {
    "install" {
        & $nssm install $serviceName $pythonw $scriptPath
        & $nssm set $serviceName AppDirectory $repoRoot
        & $nssm set $serviceName DisplayName "JARVIS — ASTRO Vault"
        & $nssm set $serviceName Description "Always-on JARVIS assistant (wake word + API)"
        # Restart on crash, with backoff
        & $nssm set $serviceName AppExit Default Restart
        & $nssm set $serviceName AppRestartDelay 5000
        # Keep it alive even when nobody is logged in (optional; comment out
        # if you only want it running while your session is active)
        & $nssm set $serviceName Type SERVICE_WIN32_OWN_PROCESS
        & net start $serviceName
        Write-Host "Service '$serviceName' installed and started. Check services.msc." -ForegroundColor Green
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
