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

:: 3. Install Core Dependencies
echo [INFO] Installing Core Libraries...
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt

:: 4. Optional Audio Driver Check (Non-Blocking)
echo [INFO] Checking Voice capabilities...
.venv\Scripts\python -c "import pyaudio" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Voice Hearing (PyAudio) requires C++ Build Tools.
    echo [WARNING] Attempting automatic fix...
    .venv\Scripts\pip install pyaudio
    if !errorlevel! neq 0 (
        echo [INFO] Voice Hearing will be disabled, but Brio's Orb is still launching!
    )
)

:: 5. Generate Professional Icon
echo [INFO] Generating High-Res Sentinel Orb Icon...
.venv\Scripts\python create_icon.py

:: 6. Create Desktop Shortcut
echo [INFO] Generating Desktop Shortcut...
set "SCRIPT_PATH=%~dp0brim_main.py"
set "ICON_PATH=%~dp0assets\brio_icon.ico"
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\Brio AI.lnk"
set "EXE_PATH=%~dp0.venv\Scripts\pythonw.exe"

:: Use PowerShell with robust quoting for spaces
powershell -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath='%EXE_PATH%'; $s.Arguments='\"%SCRIPT_PATH%\"'; $s.WorkingDirectory='%~dp0'; $s.WindowStyle=7; if(Test-Path '%ICON_PATH%'){$s.IconLocation='%ICON_PATH%'}; $s.Save()"

echo.
echo ==========================================
echo   INSTALLATION SUCCESSFUL!
echo.
echo   - Sentinel Orb: READY
echo   - Desktop Icon: APPLIED
echo   - Status: V2.2 Professional Baseline
echo.
echo   NOTE: If the icon doesn't show immediately, 
echo   right-click your Desktop and select 'Refresh'.
echo ==========================================
pause
