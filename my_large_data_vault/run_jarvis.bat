@echo off
REM JARVIS Launcher — double-click to start the tray app (no console window).

set REPO_ROOT=C:\Users\%USERNAME%\Documents\Programming\ASTRO

start "" pyw -3.13 "%REPO_ROOT%\tray_jarvis.pyw"
echo JARVIS tray app started (icon appears in the notification area).
timeout /t 3 /nobreak >nul