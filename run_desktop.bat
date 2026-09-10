@echo off
title HyperSolve Desktop - Universal Vision HUD
color 0b
cls

echo ===================================================
echo     HYPERSOLVE DESKTOP - UNIVERSAL VISION HUD
echo ===================================================
echo.

:: Detect which Python environment has PyQt6 & dependencies
set PYTHON_CMD=python
%PYTHON_CMD% -c "import PyQt6, mss, pyautogui" 2>nul
if %errorlevel% neq 0 (
    py -3.13 -c "import PyQt6, mss, pyautogui" 2>nul
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py -3.13
    ) else (
        "C:\Python313\python.exe" -c "import PyQt6, mss, pyautogui" 2>nul
        if %errorlevel% equ 0 (
            set PYTHON_CMD="C:\Python313\python.exe"
        )
    )
)

echo [ACTIVE RUNTIME] Using: %PYTHON_CMD%
echo ===================================================
echo  - Floats above ANY browser (Chrome, Brave, Edge, Firefox)
echo  - Excluded from Zoom, Teams, and Screen Shares
echo  - Press Alt + Q anywhere to solve active question
echo  - Press Ctrl + Shift + X to vanish/restore HUD
echo ===================================================
echo.

%PYTHON_CMD% desktop_main.py
pause
