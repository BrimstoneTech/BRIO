@echo off
setlocal enabledelayedexpansion

echo [Brio v3.3] Accessing Neural Pathways...

:: Get the directory of the script
set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

:: Check for the virtual environment and pythonw.exe
if not exist ".venv\Scripts\pythonw.exe" (
    echo [ERROR] Brio's brain ^(.venv^) or pythonw.exe is missing!
    echo Please run 'setup.bat' first to install him.
    pause
    exit /b 1
)

:: Run Brio seamlessly using pythonw to avoid a persistent console window
start "" ".venv\Scripts\pythonw.exe" "brio_main.py"

:: Close this window immediately
exit


