@echo off
setlocal
cd /d "%~dp0"

:: 1. Launch Chrome Profile with CDP on Port 9222 if not already running
powershell -NoProfile -Command "try { (Invoke-WebRequest -Uri 'http://127.0.0.1:9222/json' -TimeoutSec 1).StatusCode } catch { exit 1 }" 2>nul
if %errorlevel% neq 0 (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%~dp0chrome_profile" "https://chatgpt.com"
    timeout /t 2 /nobreak >nul
)

:: 2. Launch HyperSolve Command Center directly with pythonw (completely silent, no black console window)
start "" pythonw -m hypersolve.desktop.dashboard_window
exit
