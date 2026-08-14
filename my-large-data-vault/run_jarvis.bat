@echo off
REM JARVIS launcher — double-click to start the tray app (no console window).
REM Put this file anywhere you like (Desktop is convenient). Edit the
REM REPO_ROOT line below if ASTRO lives somewhere other than C:\Users\<you>\ASTRO.

set REPO_ROOT=C:\Users\%USERNAME%\ASTRO
set PYTHONW=pythonw

start "" "%PYTHONW%" "%REPO_ROOT%\my-large-data-vault\tray_jarvis.pyw"
echo JARVIS tray app started (icon appears in the notification area).
timeout /t 3 /nobreak >nul
