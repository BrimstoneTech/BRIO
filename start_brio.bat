@echo off
setlocal enabledelayedexpansion

echo [Brio v3.3] Accessing Neural Pathways...

:: Check for the virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Brio's brain (.venv) is missing!
    echo Please run 'setup.bat' first to install him.
    pause
    exit /b 1
)

:: Run Brio seamlessly
start "" ".venv\Scripts\pythonw.exe" brim_main.py

:: Close this window immediately so Brio feels like a native app
exit
