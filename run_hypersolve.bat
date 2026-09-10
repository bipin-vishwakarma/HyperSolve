@echo off
title HyperSolve - Universal Autonomous Assessment Engine
color 0b
cls

echo ===================================================
echo     HYPERSOLVE - UNIVERSAL ASSESSMENT ENGINE
echo ===================================================
echo.

:: 1. Launch Chrome with Remote Debugging
echo [1/2] Launching Chrome Profile with CDP on Port 9222...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%~dp0chrome_profile" "https://chatgpt.com"

echo Waiting for Chrome to initialize...
timeout /t 3 /nobreak >nul

:: 2. Run HyperSolve Loop
echo [2/2] Starting HyperSolve Core Daemon...
echo ===================================================
echo  - Open any Quiz or Exam tab (Moodle, Canvas, Forms)
echo  - Make sure your AI session (ChatGPT/Gemini) is logged in
echo  - HyperHUD will appear automatically on your quiz!
echo  - Panic key to vanish HUD: Ctrl + Shift + X
echo ===================================================
echo.

:run_bot
python main.py
echo.
echo [HYPERSOLVE RESTART] Engine cycle ended or refreshed.
echo Restarting monitoring mode in 3 seconds... (Press Ctrl+C to stop)
timeout /t 3 /nobreak >nul
goto run_bot
