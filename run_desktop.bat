@echo off
title HyperSolve Desktop v2.0 - Universal Vision HUD
color 0b
cls

echo ===================================================
echo     HYPERSOLVE DESKTOP v2.0 - UNIVERSAL VISION HUD
echo ===================================================
echo.

:: 1. Detect which Python environment has PyQt6 & dependencies
set PYTHON_CMD=python
%PYTHON_CMD% -c "import PyQt6, mss, pyautogui, requests" 2>nul
if %errorlevel% neq 0 (
    py -3.13 -c "import PyQt6, mss, pyautogui, requests" 2>nul
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py -3.13
    ) else (
        "C:\Python313\python.exe" -c "import PyQt6, mss, pyautogui, requests" 2>nul
        if %errorlevel% equ 0 (
            set PYTHON_CMD="C:\Python313\python.exe"
        )
    )
)

echo [ACTIVE RUNTIME] Using: %PYTHON_CMD%

:: 2. Check if Chrome with CDP is running for Zero-API-Key solving
powershell -Command "try { (Invoke-WebRequest -Uri 'http://127.0.0.1:9222/json' -TimeoutSec 1).StatusCode } catch { exit 1 }" 2>nul
if %errorlevel% neq 0 (
    echo [ZERO-KEY BRAIN] Chrome with CDP is not running yet.
    echo Launching Chrome on Port 9222 with your profile for Zero-API-Key AI...
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%~dp0chrome_profile" "https://chatgpt.com"
    timeout /t 2 /nobreak >nul
) else (
    echo [ZERO-KEY BRAIN] Connected to Chrome CDP session!
)

echo.
echo ===================================================
echo  - Floats above ANY browser (Chrome, Brave, Edge, Firefox)
echo  - Excluded from Zoom, Teams, and Screen Shares
echo  - ZERO API KEYS: Uses active ChatGPT / Gemini tab in Chrome
echo  - Press Alt + Q anywhere to solve active question
echo  - Press Ctrl + Shift + X to vanish/restore HUD
echo ===================================================
echo.

%PYTHON_CMD% desktop_main.py
pause
