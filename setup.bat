@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo       Brio AI - One-Click Installer
echo ==========================================
echo.

:: 1. Robust Python Hunt
set PYTHON_EXE=
echo [INFO] Searching for compatible Python interpreter...

:: Try 'py' (Python Launcher)
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_EXE=py
    goto :found_python
)

:: Try 'python'
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_EXE=python
    goto :found_python
)

:: Try 'python3'
python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_EXE=python3
    goto :found_python
)

:found_python
if "%PYTHON_EXE%"=="" (
    echo [ERROR] No Python interpreter found. 
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)
echo [INFO] Found: %PYTHON_EXE%

:: 2. Create Virtual Environment
if not exist .venv (
    echo [INFO] Creating Virtual Environment...
    %PYTHON_EXE% -m venv .venv
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
