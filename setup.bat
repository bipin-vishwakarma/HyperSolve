@echo off
cd /d "%~dp0"
python installer\setup_wizard.py
if errorlevel 1 pause
