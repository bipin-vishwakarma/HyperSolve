@echo off
title HyperSolve - Universal Autonomous Assessment Engine
color 0b
cls

echo ===================================================
echo     HYPERSOLVE - UNIVERSAL ASSESSMENT ENGINE
echo ===================================================
echo.

:: 0. Verify and Resolve Python Environment
set PYTHON_CMD=python
%PYTHON_CMD% -c "import playwright" 2>nul
if %errorlevel% neq 0 (
    echo [CHECK] Default python lacks playwright. Checking py launcher...
    py -3.13 -c "import playwright" 2>nul
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py -3.13
    ) else (
        echo [INSTALL] Installing playwright dependency...
        python -m pip install playwright
    )
)

:: 1. Launch Chrome with Remote Debugging
echo [1/2] Launching Chrome Profile with CDP on Port 9222...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%~dp0chrome_profile" "https://chatgpt.com"

echo Waiting for Chrome to initialize...
timeout /t 3 /nobreak >nul

:: 2. Run HyperSolve Loop
echo [2/2] Starting HyperSolve Core Daemon using %PYTHON_CMD%...
echo ===================================================
echo  - Open any Quiz or Exam tab (Moodle, Canvas, Forms)
echo  - Make sure your AI session (ChatGPT/Gemini) is logged in
echo  - HyperHUD will appear automatically on your quiz!
echo  - Panic key to vanish HUD: Ctrl + Shift + X
echo ===================================================
echo.

:run_bot
%PYTHON_CMD% main.py
echo.
echo [HYPERSOLVE RESTART] Engine cycle ended or refreshed.
echo Restarting monitoring mode in 3 seconds... (Press Ctrl+C to stop)
timeout /t 3 /nobreak >nul
goto run_bot
