@echo off
title Quiz Solver Auto-Pilot

echo [1/2] Launching Chrome Bot Profile...
set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"
:: Launch Chrome minimized so it doesn't interrupt you
start /min "" "%CHROME_PATH%" --remote-debugging-port=9222 --user-data-dir="%CD%\chrome_profile" "https://chatgpt.com" "https://learn.onlinejain.com"

echo Waiting for Chrome to initialize...
timeout /t 3 /nobreak > nul

echo [2/2] Starting Auto-Pilot Engine...
echo ===================================================
echo 1. Make sure you are logged into ChatGPT
echo 2. Make sure you are logged into Jain Online
echo 3. Navigate to your quiz
echo ===================================================
:run_bot
python full_auto.py
echo.
echo [WARNING] The Auto-Pilot script stopped or crashed!
echo Restarting automatically in 5 seconds to keep the terminal alive...
timeout /t 5 /nobreak > nul
goto run_bot
