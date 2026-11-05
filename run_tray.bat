@echo off
title HyperSolve System Tray v2.0
color 0b
cls

echo ===================================================
echo     HYPERSOLVE v2.0 - SYSTEM TRAY BACKGROUND APP
echo ===================================================
echo.

:: 1. Launch Chrome Profile with CDP on Port 9222 if not already running
powershell -Command "try { (Invoke-WebRequest -Uri 'http://127.0.0.1:9222/json' -TimeoutSec 1).StatusCode } catch { exit 1 }" 2>nul
if %errorlevel% neq 0 (
    echo [CHROME CDP] Launching Chrome on Port 9222...
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%~dp0chrome_profile" "https://chatgpt.com"
    timeout /t 2 /nobreak >nul
)

echo [TRAY] Starting HyperSolve in Windows System Tray (Notification Area)...
echo Look for the glowing cyan lightning icon next to your Windows clock!
echo.
python -m hypersolve.desktop.tray
