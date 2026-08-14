# JARVIS Windows Setup — one-command bootstrap
#
# Run from the repo root in PowerShell:
#   Set-ExecutionPolicy -Scope CurrentUser Bypass -Force   # once, if needed
#   .\setup_jarvis.ps1
#
# What it does:
#   1. Checks Python 3.10+ and pip are available (auto-installs via winget if missing)
#   2. Installs all core + assistant + voice + tray dependencies
#   3. Copies .env.example to .env if no .env exists yet
#   4. Runs the voice stack smoke test (non-blocking)
#   5. Offers to create the Windows startup shortcut (boot-time JARVIS)
#
# Re-run safely: every step is idempotent — running twice changes nothing.

$ErrorActionPreference = "Continue"

function Step($name) { Write-Host "`n==> $name" -ForegroundColor Cyan }
function Ok($msg)    { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Warn($msg)  { Write-Host "    [WARN] $msg" -ForegroundColor Yellow }

Step "Checking Python"
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Warn "Python not found — installing via winget..."
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    $py = Get-Command python
}
$version = & python --version
Ok "Found $version"

Step "Installing core pipeline dependencies"
pip install -q -r requirements.txt
Ok "core requirements installed"

Step "Installing JARVIS assistant dependencies (voice, TTS, dotenv, tray)"
pip install -q -r my_large_data_vault/requirements-jarvis.txt
Ok "jarvis requirements installed"

Step "Installing local-inference and tray extras"
pip install -q llama-cpp-python pystray Pillow uvicorn fastapi
Ok "extras installed"

Step "Seeding .env"
$envFile = "my_large_data_vault/.env"
if (-not (Test-Path $envFile)) {
    Copy-Item "my_large_data_vault/.env.example" $envFile
    Ok ".env created from .env.example — EDIT IT NOW:"
    Write-Host "    notepad $envFile" -ForegroundColor White
} else {
    Ok ".env already exists, leaving it untouched"
}

Step "Running the voice stack smoke test"
try {
    & python my_large_data_vault/test_voice_stack.py
} catch {
    Warn "smoke test could not run automatically — run it manually:"
    Write-Host "    python my_large_data_vault\test_voice_stack.py" -ForegroundColor White
}

Step "Windows startup shortcut (boot-time JARVIS)"
$answer = Read-Host "Create a startup shortcut so JARVIS launches at login? (y/n)"
if ($answer -match "^y") {
    $startup = [System.Environment]::GetFolderPath("Startup")
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut("$startup\JARVIS.lnk")
    $shortcut.TargetPath = (Get-Command pythonw).Source
    $repoRoot = (Get-Location).Path
    $shortcut.Arguments = """$repoRoot\my_large_data_vault\tray_jarvis.pyw"""
    $shortcut.WorkingDirectory = $repoRoot
    $shortcut.Description = "JARVIS — ASTRO Vault tray app"
    $shortcut.Save()
    Ok "Startup shortcut created at $startup\JARVIS.lnk"
}

Step "Done"
Write-Host "
Next steps:
  1. Edit my_large_data_vault\.env  (Llama-3 model path + API keys)
  2. pythonw my_large_data_vault\tray_jarvis.pyw   <- tray app, always on
  3. JARVIS_MODE=wake python jarvis.py             <- wake-word mode in terminal
" -ForegroundColor Green
