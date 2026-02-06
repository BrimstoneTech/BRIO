@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo       Brio AI - One-Click Installer
echo ==========================================
echo.

:: 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

:: 2. Create Virtual Environment
if not exist .venv (
    echo [INFO] Creating Virtual Environment...
    python -m venv .venv
)

:: 3. Install Dependencies
echo [INFO] Installing Libraries (this may take a minute)...
.venv\Scripts\python -m pip install --upgrade pip >nul
.venv\Scripts\pip install -r requirements.txt --quiet

:: 4. Create Desktop Shortcut
echo [INFO] Generating Desktop Shortcut...
set SCRIPT_PATH=%~dp0brim_main.py
set ICON_PATH=%~dp0assets\brio_icon.ico
set SHORTCUT_PATH=%USERPROFILE%\Desktop\Brio AI.lnk

:: Use PowerShell to create the shortcut
powershell -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT_PATH%');$s.TargetPath='.venv\Scripts\pythonw.exe';$s.Arguments='\"%SCRIPT_PATH%\"';$s.WorkingDirectory='%~dp0';$s.WindowStyle=7;if(Test-Path '%ICON_PATH%'){$s.IconLocation='%ICON_PATH%'};$s.Save()"

echo.
echo ==========================================
echo   INSTALLATION COMPLETE!
echo.
echo   You can now launch Brio from your Desktop.
echo ==========================================
pause
